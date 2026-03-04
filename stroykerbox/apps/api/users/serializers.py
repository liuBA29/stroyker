from rest_framework import serializers

from stroykerbox.apps.users import models as user_models


class UserDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_models.UserDocument
        fields = ['name', 'doc_date', 'file']

    def create(self, validated_data):
        user_id = self.initial_data.get('user')
        validated_data['user_id'] = user_id
        return super().create(validated_data)


class UserSerializer(serializers.ModelSerializer):
    discount_group = serializers.StringRelatedField(read_only=True)
    documents = UserDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = user_models.User
        fields = ['id', 'email', 'name', 'company', 'phone', 'is_active',
                  'date_joined', 'calculation', 'discount', 'discount_group', 'documents']
        lookup_field = 'email'
