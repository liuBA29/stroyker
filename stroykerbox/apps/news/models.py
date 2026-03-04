import os

from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from sorl.thumbnail import ImageField


NEWS_POST_TYPE_NEWS, NEWS_POST_TYPE_PROMO = 'news', 'promo'


class News(models.Model):
    """
    News or Promo object.
    """

    title = models.CharField(_('title'), max_length=255)
    slug = models.SlugField(unique=True)
    image = ImageField(_('image'), upload_to='news', blank=True)
    date = models.DateField(_('date'), db_index=True)
    teaser = models.TextField(_('teaser text'))
    text = models.TextField(_('text'))
    post_type = models.CharField(
        _('post type'),
        max_length=7,
        default=NEWS_POST_TYPE_NEWS,
        choices=[(NEWS_POST_TYPE_NEWS, _('news')), (NEWS_POST_TYPE_PROMO, _('promo'))],
        help_text=_('Type of publication - news or promotion.'),
    )
    wide_view = models.BooleanField(_('wide view mode'), default=False)
    published = models.BooleanField(
        _('show on the site'),
        db_index=True,
        default=True,
    )
    use_custom_form = models.BooleanField(
        _('use custom form'),
        default=False,
        help_text=_(
            'Uses the custom form inside text. '
            'To insert the desired custom form use the syntax: {% custom_form "CUSTOM-FORM-KEY" %}'
        ),
    )
    meta_keywords = models.TextField(_('meta keywords'), blank=True, null=True)
    meta_description = models.TextField(_('meta description'), blank=True, null=True)

    updated_at = models.DateTimeField(_('update date'), auto_now=True)

    # https://redmine.nastroyker.ru/issues/19241
    use_editor = models.BooleanField(
        'использовать редактор',
        default=True,
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        if self.post_type == NEWS_POST_TYPE_PROMO:
            return reverse('news:promo_details', kwargs={'slug': self.slug})
        return reverse('news:news_details', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = _('news/promo item')
        verbose_name_plural = _('news/promo items')


class NewsAttachAbstract(models.Model):
    title = models.CharField(_('title'), max_length=140, null=True, blank=True)
    news = models.ForeignKey(News, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(
        _('position'), db_index=True, default=0, blank=True
    )

    class Meta:
        abstract = True


class NewsImage(NewsAttachAbstract):
    """
    One Image object for the news or promo item.
    """

    image = models.FileField(_('image'), upload_to='news')

    class Meta:
        ordering = ['position', 'id']
        verbose_name = _('image')
        verbose_name_plural = _('images')
        default_related_name = 'images'

    def __str__(self):
        return self.title or os.path.basename(self.image.name)

    @property
    def alt_text(self):
        return self.title or self.news.title


class NewsFile(NewsAttachAbstract):
    """
    One File object for the news or promo item.
    """

    file = models.FileField(_('file'), upload_to='news')

    class Meta:
        ordering = ['position', 'id']
        verbose_name = _('file')
        verbose_name_plural = _('files')
        default_related_name = 'files'

    def __str__(self):
        return self.title or os.path.basename(self.file.name)
