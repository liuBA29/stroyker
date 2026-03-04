from django.db import models
from django.shortcuts import reverse
from django.utils.functional import cached_property
from sorl.thumbnail import ImageField


class PortfolioCategory(models.Model):
    name = models.CharField('название', max_length=64)
    position = models.PositiveSmallIntegerField('позиция', default=0)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ('position',)
        verbose_name = 'категория портфолио'
        verbose_name_plural = 'категории портфолио'

    def __str__(self):
        return self.name


class Portfolio(models.Model):
    name = models.CharField('название', max_length=128)
    image = ImageField(
        'фото для тизера', upload_to='portfolio/images', null=True, blank=True
    )
    description = models.TextField('описание', null=True, blank=True)
    category = models.ForeignKey(
        PortfolioCategory,
        verbose_name='категория',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    position = models.PositiveSmallIntegerField('позиция', default=0)
    published = models.BooleanField(
        'отображать на сайте',
        default=True,
    )
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ('position',)
        verbose_name = 'портфолио'
        verbose_name_plural = 'портфолио'

    def __str__(self):
        return self.name

    @cached_property
    def teaser_image(self):
        if self.image:
            return self.image
        if first_image := self.images.first():
            return first_image.image

    def get_absolute_url(self):
        return reverse('portfolio:detail', kwargs=({'slug': self.slug}))


class PortfolioImage(models.Model):
    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name='images'
    )
    image = ImageField('фото', upload_to='portfolio/images')
    position = models.PositiveSmallIntegerField('позиция', default=0)

    class Meta:
        ordering = ('position',)
        verbose_name = 'фото портфолио'
        verbose_name_plural = 'фотографии портфолио'

    def __str__(self):
        return self.image.name
