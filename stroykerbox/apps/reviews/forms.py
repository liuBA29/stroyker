from django import forms
from django.utils.translation import ugettext as _
from django.template.defaultfilters import wordcount

from .models import ProductReview


class ProductReviewForm(forms.ModelForm):
    """
    Product review form
    """

    class Meta:
        model = ProductReview
        fields = [
            'review_text',
            'rating_value',
        ]
        sequence = [
            'review_text',
            'rating_value',
        ]
        widgets = {
            'review_text': forms.Textarea(
                attrs={'rows': '2', 'class': 'form-control',
                       'placeholder': _('Your product review')}),
            'rating_value': forms.HiddenInput(),
        }

    class Media:
        js = ('reviews/js/review_form.js',)

    def __init__(self, user, product, *args, **kwargs):
        self.user = user
        self.product = product
        super().__init__(*args, **kwargs)

    def clean_review_text(self):
        review_text = self.cleaned_data.get('review_text')
        if wordcount(review_text) < 5:
            raise forms.ValidationError(
                _('The review must contain at least 5 words'))
        return review_text

    def clean_rating_value(self):
        rating_value = self.cleaned_data.get('rating_value')
        if not rating_value:
            raise forms.ValidationError(_('The review must contain the rating value'))
        return rating_value

    def save(self, commit=True):
        review = super().save(commit=False)
        review.user = self.user
        review.product = self.product
        if commit:
            review.save()
        return review
