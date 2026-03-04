from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest, JsonResponse
from django.core import serializers
from django.utils.translation import ugettext as _

from stroykerbox.apps.catalog.models import Product

from .models import ProductReview, ProductReviewHelpfulness
from .forms import ProductReviewForm
from .tasks import send_review_notification_email_manager


def get_review_list(request, product_pk):
    reviews = ProductReview.objects.filter(product=product_pk, published=True)
    if reviews:
        response = serializers.serialize('json', reviews)
        return JsonResponse(response, safe=False)
    else:
        response = {
            'success': False,
            'errors': _('There are no reviews for this product yet, but you can be the first!'),
        }
        return JsonResponse(response)


def review_add(request, product_pk):
    """Ajax review add view"""
    if request.is_ajax() and request.method == 'POST':
        response = {'success': False}

        if not request.user.is_authenticated:
            response['errors'] = _('You must be logged in to add a review.')
            return JsonResponse(response)

        elif ProductReview.objects.filter(user=request.user, product_id=product_pk).exists():
            response['errors'] = _(
                'You have already left review for this product. This can only be done once.')
            return JsonResponse(response)

        product = get_object_or_404(Product, pk=product_pk)
        form = ProductReviewForm(request.user, product, request.POST)

        if form.is_valid():
            review = form.save()
            response['success'] = True
            response['message'] = _('Thanks. Your review has been received.')
            send_review_notification_email_manager.delay(review)

            return JsonResponse(response)
        else:
            response['errors'] = form.errors
            return JsonResponse(response)

    return HttpResponseBadRequest('Bad request')


def review_delete(request, review_pk):
    review = get_object_or_404(ProductReview, pk=review_pk)
    review.delete()


def create_helpfulness_object(user, review_pk, value):
    """
    Creating a helpfulness object for the review.
    """
    response = {'success': False}
    if not user.is_authenticated:
        response['errors'] = _(
            'You must be logged in to add your vote for this review.')
        return response
    if ProductReviewHelpfulness.objects.filter(user=user, review_id=review_pk).exists():
        response['errors'] = _(
            'Each user can vote for the usefulness of a separate review only once.')
        return response

    review = ProductReview.objects.filter(pk=review_pk).first()

    if review:
        ProductReviewHelpfulness.objects.create(
            user=user, review=review, is_helpful=value)
        response['success'] = True
        response['advantage'] = review.advantage

    return response


def review_is_usefully(request, review_pk):
    response = create_helpfulness_object(request.user, review_pk, True)
    return JsonResponse(response)


def review_is_useless(request, review_pk):
    response = create_helpfulness_object(request.user, review_pk, False)
    return JsonResponse(response)
