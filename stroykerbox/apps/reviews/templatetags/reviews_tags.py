from django import template
from django.db.models import Avg

from stroykerbox.apps.reviews.models import ProductReview
from stroykerbox.apps.reviews.forms import ProductReviewForm

register = template.Library()


@register.inclusion_tag('reviews/tags/review-form.html', takes_context=True)
def render_review_form(context, product):
    user = getattr(context['request'], 'user', None)
    context['form'] = ProductReviewForm(user, product)

    return context


@register.inclusion_tag('reviews/tags/product-reviews.html')
def render_product_reviews(product=None):
    if product:
        reviews = ProductReview.objects.published().filter(product=product)
        return {'reviews': reviews}


@register.inclusion_tag('reviews/tags/rating-five-stars.html')
def render_rating_five_stars(rating=None):
    return {'rating': rating, 'rating_range': range(1, 6)}


@register.inclusion_tag('reviews/tags/product-average-rating.html')
def render_product_average_rating(product_pk, fake_rating=None):
    if fake_rating:
        average_rating = fake_rating
    else:
        average_rating = ProductReview.objects.published().filter(
            product_id=product_pk, rating_value__gt=0).aggregate(average_rating=Avg('rating_value'))['average_rating']
    return {'rating': average_rating}


@register.simple_tag
def product_reviews_counter(product_pk):
    return ProductReview.objects.published().filter(
        product_id=product_pk).count()


@register.simple_tag
def product_votes_counter(product_pk):
    return ProductReview.objects.published().filter(
        product_id=product_pk, rating_value__gt=0).count()


@register.inclusion_tag('reviews/tags/reviews-list-8march.html')
def render_reviews_for_8march(limit=10):
    """Последние опубликованные отзывы о товарах для секции ОТЗЫВЫ на странице 8 марта."""
    reviews = ProductReview.objects.published().select_related('product', 'user').order_by('-created_at')[:limit]
    return {'reviews': reviews}
