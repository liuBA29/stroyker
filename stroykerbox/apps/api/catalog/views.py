# type: ignore
import os
from urllib.parse import urlparse

import requests
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAdminUser, AllowAny
from django.core.files.base import ContentFile, File
from django.http import Http404
from django.conf import settings

from stroykerbox.apps.catalog.models import Product, Category, Stock, Uom, ProductImage
from stroykerbox.apps.locations.models import Location
from stroykerbox.apps.api.permissions import AllowedKey, AllowedIP
from stroykerbox.apps.drf_tracker.mixins import LoggingMixin

from .serializers import (
    ProductSerializer,
    ProductListSerializer,
    ProductStockSerializer,
    ProductPriceSerializer,
    CategorySerializer,
    WarehouseSerializer,
    UomSerializer,
    ProductImageSetSerializer,
    ProductImageFromUrlSerializer,
)


class LocationMixin:
    def get_serializer_context(self):
        """
        pass current location object to serializer context
        """
        context = super().get_serializer_context()
        context['location'] = None
        location = (
            self.request.query_params.get('location')
            if hasattr(self.request, 'query_params')
            else None
        )
        if location:
            try:
                location_object = Location.objects.get(pk=location)
            except Location.DoesNotExist:
                pass
            else:
                if not Location.check_default(location_object):
                    context['location'] = location_object

        return context


class ProductViewSet(LoggingMixin, LocationMixin, viewsets.ModelViewSet):
    """
    List, create and update catalog products.

    retrieve:
    Return the given product.

    list:
    Return a list of all the existing products.

    create:
    Create a new product instance.

    update:
    Update the given product instance.

    partial_update:
    Partial update the given product instance.

    delete:
    Delete the given product instance.
    """

    queryset = Product.objects.select_related(
        'price_type',
        'uom',
    ).prefetch_related('categories')
    lookup_field = 'sku'
    if settings.DEBUG:
        permission_classes = [AllowAny]
    else:
        permission_classes = [IsAdminUser | AllowedKey | AllowedIP]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ('retrieve', 'list'):
            queryset = queryset.prefetch_related('params', 'props', 'images')
        return queryset


class ProductStockViewSet(LoggingMixin, LocationMixin, viewsets.ModelViewSet):
    serializer_class = ProductStockSerializer
    queryset = Product.objects.all()
    lookup_field = 'sku'
    http_method_names = ['get', 'patch']


class ProductPriceViewSet(LoggingMixin, LocationMixin, viewsets.ModelViewSet):
    """
     partial_update:
         При обновлении передавать НАЗВАНИЕ ГОРОДА (не НАЗВАНИЕ РЕГИОНА, заданное для склада).
     JSON Example for "location_prices" data:
     <pre>
    "location_prices": [
      {
          "location": "Самара",
          "price": "37927.00",
          "old_price": "73773.00",
          "purchase_price": "7387927.00"
      },
      {
          "location": "Уфа",
          "price": "736826.00",
          "old_price": "87397.00",
          "purchase_price": "7979.00" }
    ]
    </pre>
    """

    serializer_class = ProductPriceSerializer
    queryset = Product.objects.all()
    lookup_field = 'sku'
    http_method_names = ['get', 'patch']
    if settings.DEBUG:
        permission_classes = [AllowAny]
    else:
        permission_classes = [IsAdminUser | AllowedKey | AllowedIP]


class CategoryViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    List, create and update catalog products.

    retrieve:
    Return the given category.

    list:
    Return a list of all existing categories.

    create:
    Create a new category instance.

    update:
    Update the given category instance.

    partial_update:
    Partial update the given product category.

    delete:
    Delete the given category instance.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class WarehouseViewSet(LoggingMixin, LocationMixin, viewsets.ModelViewSet):
    """
    List, create and update catalog products.

    retrieve:
    Return the given warehouse.

    list:
    Return a list of all the existing warehouses.

    create:
    Create a new warehouse instance.

    update:
    Update the given warehouse instance.

    partial_update:
    Partial update the given warehouse.

    delete:
    Delete the given warehouse instance.
    """

    queryset = Stock.objects.all()
    serializer_class = WarehouseSerializer


class ProductUomViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    List, create and update product units (uom).

    retrieve:
    Return the given unit.

    list:
    Return a list of all existing product units.

    create:
    Create a new product unit instance.

    update:
    Update the given product unit instance.

    partial_update:
    Partial update the given product unit.

    delete:
    Delete the given product unit instance.
    """

    queryset = Uom.objects.all()
    serializer_class = UomSerializer


class ProductImagesDeleteView(LoggingMixin, APIView):
    """
    Delete a product images by POST with json data.
    """

    def post(self, request, product_sku, format=None):
        """
        Удаление изображений товара методом POST.
        <pre>
        Пример ожидаемых данных в JSON-формате.
        В качестве идентификатора изображения должен быть
        путь относительно каталога "media" или путь как в
        URL на изображение (относительный URL: /media/path/to/image.jpg):
         {
            "images": [
                {
                    "image": "/products/images/img1.png",
                },
                {
                    "image": "/products/images/img2.jpg",
                }
            ]
          }
        </pre>

        <pre>
        Пример отправки данных с помощьюд CURL:

        curl -X POST -S
            -H 'Content-Type: application/json'
            -H 'Authorization: Token {header_token_key}'
            -d '{
                "images": [
                  {
                   "image": "/products/images/img1.png",
                  },
                  {
                   "image": "/products/images/img2.jpg",
                  }
                 ]}'
            http://stroykerbox.local/api/v1/product-images/683333223/
        </pre>
        """
        try:
            product = Product.objects.get(sku=product_sku)
        except Product.DoesNotExist:
            raise Http404(f'Product with sku {product_sku} does not exist.')

        images = [
            image['image'].replace(settings.MEDIA_URL, '')
            for image in request.data.get('images', [])
        ]

        ProductImage.objects.filter(product=product, image__in=images).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImagesView(LoggingMixin, APIView):
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get(self, request, product_sku):
        """
        <pre>
        Пример отправки данных с помощьюд CURL:
        curl -X GET
          -H 'Authorization: Token {header_token_key}'
          http://site.url/api/v1/product-images/3293799/
        </pre>
        """
        product = self.get_product_by_sku(product_sku)
        images = ProductImage.objects.filter(product=product)
        serializer = ProductImageSetSerializer(images, many=True)
        return Response({'images': serializer.data})

    def get_image_file(self, url_or_path):
        img_file = None
        name = urlparse(url_or_path).path.split('/')[-1]

        if url_or_path.startswith('http'):
            response = requests.get(url_or_path)
            if response.status_code == 200:
                img_file = ContentFile(response.content)
        else:
            file_path = os.path.join(
                settings.MEDIA_ROOT, url_or_path.lstrip(os.path.sep)
            )
            if os.path.exists(file_path):
                img_file = File(open(file_path, 'rb'))
                os.remove(file_path)

        return name, img_file

    def get_product_by_sku(self, sku):
        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            raise Http404(f'Product with sku {sku} does not exist.')
        return product

    def put(self, request, product_sku, format=None):
        """
        Обновление позиций для существующих изображений для товаров.

        <pre>
        Пример ожидаемых данных в JSON-формате.
        В качестве идентификатора изображения должен быть
        путь относительно каталога "media" или путь как в
        URL на изображение (относительный URL: /media/path/to/image.jpg):
         {
            "images": [
                {
                    "image": "/products/images/img1.png",
                    "position": 22
                },
                {
                    "image": "/products/images/img2.jpg",
                    "position": 3
                }
            ]
          }
        </pre>

        <pre>
        Пример отправки данных с помощьюд CURL:
        curl -X POST -S
            -H 'Content-Type: application/json'
            -H 'Authorization: Token {header_token_key}'
            -d '{
                "images": [
                    {
                        "image": "/products/images/img1.png",
                        "position": 0
                    },
                    {
                        "image": "/products/images/img2.jpg",
                        "position": 1
                    }
                ]
                }'
            http://stroykerbox.local/api/v1/product-images/683333223/
        </pre>
        """
        product = self.get_product_by_sku(product_sku)
        images = request.data.get('images', [])
        data = []

        for image in images:
            if ProductImage.objects.filter(
                product=product, image=image['image'].replace(settings.MEDIA_URL, '')
            ).update(position=image.get('position', 0)):
                data.append(image)

        return Response(data=data, status=status.HTTP_201_CREATED)

    def post_as_json(self, request, product_sku, format=None):
        product = self.get_product_by_sku(product_sku)
        images = request.data.get('images', [])
        data = []

        for image in images:
            serializer = ProductImageFromUrlSerializer(
                data={'image': image['image'], 'position': image.get('position', 0)}
            )

            if serializer.is_valid():

                name, img_file = self.get_image_file(image['image'])

                if img_file:
                    p = serializer.save(
                        product=product,
                    )
                    if name:
                        p.image.save(name, img_file, save=True)
                    else:
                        p.image = img_file
                        p.save()

                data.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=data, status=status.HTTP_201_CREATED)

    def post(self, request, product_sku, format=None):
        """
        Создание новых изображений для конкретного товара.
        <pre>
        Пример ожидаемых данных в JSON-формате.
        Для вариантов, когда передается url или путь до локального файла.
        В качестве идентификатора изображения должен быть
        путь относительно каталога "media" или путь как в
        URL на изображение (относительный URL: /media/path/to/image.jpg):

        {
           "images": [
               {
                   "image": "/products/images/img1.png",
                   "position": 22
               },
               {
                   "image": "/products/images/img2.jpg",
                   "position": 3
               }
           ]
        }
        </pre>
        <pre>
        Пример для CURL (с передачей файла как URL или пути к локальному файлу):
        curl -X POST -S
            -H 'Content-Type: application/json'
            -H 'Authorization: Token {header_token_key}'
            -d '{
                "images": [
                    {
                        "image": "/products/images/img1.png",
                        "position": 0
                    },
                    {
                        "image": "/products/images/img2.jpg",
                        "position": 1
                    }
                ]
                }'
            http://stroykerbox.local/api/v1/product-images/683333223/
        </pre>

        <pre>
        Пример для CURL (с передачей непосредственно самого файла (как поток байтов)):
        curl -X POST -S
          -H 'Accept: application/json'
          -H 'Content-Type: multipart/form-data'
          -H 'Authorization: Token {header_token_key}'
          -F "image=@/path/to/some_image.jpg;type=image/jpg"
          -F "position=0" \
          http://site.url/api/v1/product-images/3293799/
        </pre>
        """
        if request.content_type == 'application/json':
            return self.post_as_json(request, product_sku, format)

        elif 'multipart/form-data' in request.content_type:
            serializer = ProductImageSetSerializer(data=request.data)

            if serializer.is_valid():

                serializer.save(
                    product=self.get_product_by_sku(product_sku),
                    image=request.data.get('image'),
                    position=request.data.get('position', 0),
                )

                return Response(data=serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductBulkUpdateBase(LoggingMixin, APIView):
    permission_classes = [IsAdminUser | AllowedKey | AllowedIP]

    def get_object(self, sku):
        try:
            return Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            pass


class ProductPricesBulkUpdate(ProductBulkUpdateBase):

    def put(self, request):
        """
        Пример ожидаемых данных в JSON-формате.
        <pre>
            [
                {
                    "sku": "002124",
                    "currency": "rub",
                    "price": "1220.00",
                    "location_prices": [],
                    "multiplicity": "1.00000",
                    "multiplicity_label": null
                },
                {
                    "sku": "FM-00001",
                    "price": "1350.00",
                    "location_prices": [],
                    "multiplicity": "1.00000",
                    "multiplicity_label": null
                },
                {
                    "sku": "FM-00013",
                    "price": "1350.00",
                    "location_prices": [],
                    "multiplicity": "1.00000",
                    "multiplicity_label": null
                }
            ]
        </pre>
        """
        output = []
        for item_data in request.data:
            product = self.get_object(sku=item_data.get('sku'))
            if not product:
                continue

            serializer = ProductPriceSerializer(product)
            serializer.update(product, item_data)
            output.append(serializer.data)

        return Response(data=output, status=200)


class ProductStocksBulkUpdate(ProductBulkUpdateBase):

    def put(self, request):
        """
        Пример ожидаемых данных в JSON-формате.
        <pre>
            [
                {
                    "sku": "1025020",
                    "stocks_availability": [
                        {
                            "available": 120.0,
                            "warehouse": {
                                "id": 1
                            }
                        }
                    ]
                },
                {
                    "sku": "1029645",
                    "stocks_availability": [
                        {
                            "available": 99.0,
                            "warehouse": {
                                "id": 1
                            }
                        }
                    ]
                }
            ]
        </pre>
        """
        output = []
        for item_data in request.data:
            product = self.get_object(sku=item_data.get('sku'))
            if not product:
                continue

            serializer = ProductStockSerializer(product)
            serializer.update(product, item_data)
            output.append(serializer.data)

        return Response(data=output, status=200)
