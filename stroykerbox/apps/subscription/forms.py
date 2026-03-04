from django.forms import ModelForm

from .models import Subscription


class SubscriptionForm(ModelForm):

    class Meta:
        model = Subscription
        fields = ('email',)

    class Media:
        js = ('subscription/js/subscription.js',)
