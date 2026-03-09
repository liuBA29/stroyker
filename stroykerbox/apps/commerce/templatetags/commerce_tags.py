from django import template

from stroykerbox.apps.commerce.cart import Cart


register = template.Library()


@register.inclusion_tag('commerce/tags/cart-info-block.html', takes_context=True)
def render_cart(context):
    context['cart'] = Cart.from_request(context['request'])
    return context


@register.inclusion_tag('commerce/tags/mini-cart-8march.html', takes_context=True)
def render_mini_cart_8march(context):
    """Мини-корзина 8 марта: до 2 товаров с фото для выдвижной панели. Чтобы отключить — см. includes/mini_cart_8march.html и base.html (8march_mini_cart.css)."""
    request = context.get('request')
    if not request:
        return {}
    cart = Cart.from_request(request)
    items = []
    for i, item in enumerate(cart):
        if i >= 2:
            break
        items.append(item)
    context['cart'] = cart
    context['mini_cart_items'] = items
    return context


@register.inclusion_tag('commerce/tags/login-form.html', takes_context=True)
def render_commerce_login_form(context):
    from django.contrib.auth.forms import AuthenticationForm
    context['form'] = AuthenticationForm()
    context['next'] = context.get('request').path
    return context


@register.simple_tag()
def get_ajax_cost_url(delivery_form):
    """
    URI, upon access to which, through ajax, the cost of delivery for
    a particular form of delivery will be calculated.
    """
    return delivery_form._meta.model.get_cost_url() or ''


@register.simple_tag(takes_context=True)
def product_cart_price(context, product, order=None):
    # if is order notify - getting order
    if order:
        return (product.online_price(order.user, order.location) or
                product.personal_price(order.user, order.location))
    # if is the cart page - getting cart
    cart = context.get('cart')
    if cart:
        return cart.product_cart_price(product)


@register.inclusion_tag('cart/tags/cart-products.html', takes_context=True)
def render_cart_products(context, cart):
    context['cart'] = cart
    return context


@register.simple_tag(takes_context=True)
def cart_count_products(context):
    if 'cart' in context:
        return len(context['cart'])
    cart = Cart.from_request(context['request'])
    return len(cart)
