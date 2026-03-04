from django.db import models
from django.conf import settings
from django.utils.translation import ugettext as _


NO_RATE, ONE, TWO, THREE, FOUR, FIVE = range(6)
RATING_CHOICES = (
    (NO_RATE, _('no rating')),
    (ONE, _('very bad')),
    (TWO, _('bad')),
    (THREE, _('satisfactory')),
    (FOUR, _('well')),
    (FIVE, _('very well')),
)


class ProductReviewManager(models.Manager):
    def published(self):
        return self.filter(published=True)


class ProductReview(models.Model):
    """
    The product review model.
    With a 5-star rating for the product and self-rating.
    """
    product = models.ForeignKey('catalog.Product', related_name='reviews', on_delete=models.CASCADE,
                                verbose_name=_('name'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, related_name='reviews')
    rating_value = models.PositiveSmallIntegerField(_('rating'), choices=RATING_CHOICES,
                                                    default=NO_RATE)
    review_text = models.TextField(_('review text'), blank=True, null=True)
    created_at = models.DateTimeField(_('created date'), auto_now_add=True)
    published = models.BooleanField(_('published'), default=False)

    objects = ProductReviewManager()

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-rating_value', '-created_at']
        verbose_name = _('product review')
        verbose_name_plural = _('product reviews')

    def __str__(self):
        return _('review from %(self_user)s for "%(product_name)s"') % {
            'self_user': self.user, 'product_name': self.product.name}

    @property
    def usefully(self):
        return self.review_helpfulness.filter(is_helpful=True).count()

    @property
    def useless(self):
        return self.review_helpfulness.filter(is_helpful=False).count()

    @property
    def advantage(self):
        return self.usefully - self.useless


class ProductReviewHelpfulness(models.Model):
    review = models.ForeignKey(ProductReview, on_delete=models.SET_NULL,
                               null=True, related_name='review_helpfulness')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, related_name='review_helpful_votes')
    is_helpful = models.BooleanField(_('review is helpful'))

    class Meta:
        unique_together = ('review', 'user')
