from collections import defaultdict
import types

from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from constance import config
from stroykerbox.apps.catalog.models import Product

from .models import Order


class CartValidationError(Exception):
    pass


class CartException(Exception):
    pass


class ItemAlreadyAdded(CartException):
    pass


class ItemUnavailable(CartException):
    pass


class WrongQuantity(CartException):
    pass


class ProductNotFound(CartException):
    pass


class UserNotAuthenticated(CartException):
    pass


def not_empty_cart_required(redirect_to='cart:cart'):
    """
    View decorator which checks if cart is empty or not.
    If cart is empty perform a redirect.
    """

    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            cart_serialized = request.session.get('cart')
            if cart_serialized is None or ('products' in cart_serialized and len(cart_serialized['products']) == 0):
                return redirect(redirect_to)
            else:
                return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


class lazyproperty(object):
    def __init__(self, func):
        self.func = func
        self.attr_name = '_cached_{}'.format(func.__name__)

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            if not hasattr(instance, self.attr_name) or getattr(instance, self.attr_name) is None:
                setattr(instance, self.attr_name, self.func(instance))
            return getattr(instance, self.attr_name)

    def __set__(self, instance, value):
        setattr(instance, self.attr_name, value)


def invalidates(*attrs):
    class Decorator(object):
        def __init__(self, func):
            self.func = func

        def __call__(self, *args, **kwargs):
            instance = args[0]
            result = self.func(*args, **kwargs)
            for attr in attrs:
                setattr(instance, attr, None)
            return result

        def __get__(self, instance, cls):
            if instance is None:
                return self
            else:
                return types.MethodType(self, instance)

    return Decorator


def then_call(*funcs):
    class Decorator(object):
        def __init__(self, func):
            self.func = func

        def __call__(self, *args, **kwargs):
            instance = args[0]
            result = self.func(*args, **kwargs)
            for func in funcs:
                func(instance)
            return result

        def __get__(self, instance, cls):
            if instance is None:
                return self
            else:
                return types.MethodType(self, instance)

    return Decorator


class Cart(object):
    """
    Items cart. Stores items' primary keys only without any additional information.
    """

    def __init__(self, user, request=None):
        self.user = user
        self.location = getattr(request, 'location', None)
        self.products = defaultdict(int)
        self.order = None
        self.events_log = []

    @invalidates('total_products_price', 'total_count')
    def reset(self):
        """
        Reset cart contents
        """
        self.products = defaultdict(int)
        self.order = None

    @classmethod
    def from_request(cls, request):
        """
        Create a Cart instance from a Django request
        """
        # check if cart exists in a session
        cart_serialized = request.session.get('cart')
        if cart_serialized:
            # Recreate a cart state by sequentially applying all the data we have.
            cart = cls(request.user, request)
            # Add items.
            products_to_delete = set()
            for product_pk, quantity in cart_serialized.get('products', {}).items():
                try:
                    cart.add_product(Product.objects.get(
                        pk=product_pk), quantity)
                except (CartException, Product.DoesNotExist) as e:
                    cart.events_log.append(
                        _('Could not add a product to the cart: {}'.format(str(e))))
                    # Remove the product from the cart.
                    products_to_delete.add(product_pk)

            if products_to_delete:
                for product_pk in products_to_delete:
                    del cart_serialized['products'][product_pk]

                request.session.save()

            # Add order info.
            order_pk = cart_serialized.get('order_pk')
            if order_pk is not None:
                try:
                    cart.order = Order.objects.get(
                        pk=order_pk) if order_pk else None
                except Order.DoesNotExist:
                    # Order has been deleted from DB (probably from admin interface)
                    pass
            return cart
        else:
            return cls(request.user)

    def save_to_session(self, session):
        session['cart'] = {
            'products': self.products,
            'order_pk': self.order.pk if self.order else None
        }

    @invalidates('total_products_price', 'total_count')
    def add_product(self, product, quantity=1):
        """
        Add item to cart.
        """
        if not product.is_available(self.location):
            raise ItemUnavailable()
        if product.pk in self.products:
            new_qty = (self.products[product.pk] + quantity)
            self.update_quantity(product, new_qty)
        else:
            self.products[product.pk] += quantity

    @invalidates('total_products_price', 'total_count')
    def remove_product(self, product):
        """
        Remove item from cart.
        """
        try:
            del self.products[product.pk]
        except KeyError:
            raise ProductNotFound(_('Product was not found in the cart'))

    @invalidates('total_products_price', 'total_count')
    def update_quantity(self, product, quantity):
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            raise WrongQuantity(_('Product quantity is not a number'))
        if quantity <= 0:
            raise WrongQuantity(_('Wrong number for product quantity'))

        if not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE and product.is_available(self.location):
            available_items_count = product.available_items_count(
                self.location)
            if available_items_count < quantity:
                raise WrongQuantity(_('Wrong number for product quantity'))

        self.products[product.pk] = quantity
        return quantity

    def __contains__(self, product):
        return product.pk in self.products

    def __len__(self):
        """
        Number of the unique items in the cart
        """
        return len(self.products)

    @property
    def total_weight(self):
        if self.order:
            return self.order.total_weight
        return round(sum(p.weight * q for p, q in self if p.weight), 2)

    @property
    def total_volume(self):
        return round(sum(p.volume * q for p, q in self if p.volume), 2)

    @lazyproperty
    def total_count(self):
        """
        Total count number of the products (sum of quantities)
        """
        return sum(self.products.values())

    def __nonzero__(self):
        return bool(len(self))

    def product_cart_price(self, product):
        return (product.online_price(self.user, self.location) or
                product.personal_price(self.user, self.location))

    @lazyproperty
    def total_products_price(self):
        """
        Return total price of products with all the discounts applied.
        """
        total = 0
        for product, quantity in self:
            # Product price with a personal discount applied.
            total += self.product_cart_price(product) * quantity

        return total

    @property
    def total_price(self):
        """
        Return total price of products with all the discounts applied.
        """
        # ...
        # Here is some code that changes, perhaps the total price
        # ...

        return self.total_products_price

    @property
    def delivery_cost(self):
        """
        Order delivery cost
        """
        if self.order and self.order.delivery:
            return self.order.delivery.cost()
        return 0

    @property
    def final_price(self):
        """
        Final price to be charged from customer for this order
        """
        return self.total_price + self.delivery_cost

    @property
    def base_price(self):
        """
        Return price of products with no personal discounts applied.
        """
        # ...
        # Here is some code that changes, perhaps the total price
        # ...
        return self.total_price

    def __iter__(self):
        """
        Iterator which yields product objects rather than primary keys.
        """
        marked_for_deletion = []

        class ProductMock(object):
            def __init__(self, pk):
                self.pk = pk

        for pk, quantity in self.products.items():
            try:
                yield (Product.objects.get(pk=pk), quantity)
            except Product.DoesNotExist:
                marked_for_deletion.append(ProductMock(pk))

        for product in marked_for_deletion:
            self.remove_product(product)


def memoize(func):
    """Simple memoization decorator. Supports positional arguments only."""
    func.cache = {}

    def wrapper(*args):
        return func.cache.setdefault(args, func(*args))

    return wrapper
