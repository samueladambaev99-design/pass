from rest_framework import serializers
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from app.users.models import PasswordResetCode

from app.product.models import (
    Category, Models, Product, ProductImage, Favorite,
    CartItem, Cart, Order, OrderItem
)

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']

class ProductSerializer(serializers.ModelSerializer):
    first_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            'user',
            "uuid",
            "title",
            "description",
            "price",
            "first_image"
        ]

    def get_first_image(self, obj):
        first_img = obj.images.first()
        if first_img:
            return first_img.image.url
        return None

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_title = serializers.CharField(source='category.title', read_only=True)
    model_title = serializers.CharField(source='model.title', read_only=True)

    class Meta:
        model = Product
        fields = [
            "id","user", "uuid", "title", 
            "description", "price", 
            "created_at", "size", 
            "is_active",
            "images", "model_title", "category_title"
        ]

class ProductCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Product
        fields = [
            'title','description', 'price', 'size',
            'category', 'model', 'images'
        ]

    def validate_title(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Название должно быть минимум 3 символа!")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должно быть больше 0!")
        return value

    def validate_size(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("Размер слишком длинный!")
        return value

    def validate(self, attrs):
        category = attrs.get("category")
        model = attrs.get("model")

        if model and category and model.category != category:
            raise serializers.ValidationError(
                "Модель не принадлежит выбранной категории!"
            )

        return attrs

    def create(self, validated_data):
        images_data = validated_data.pop("images", [])

        request = self.context.get("request")  

        product = Product.objects.create(
            user=request.user,
            **validated_data
        )

        for img in images_data:
            ProductImage.objects.create(product=product, image=img)

        return product

class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ["id", "user", "product"]
        read_only_fields = ["id", "created_at"]

class CartItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.IntegerField(source="product.price", read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id", "product", "product_title",
            "product_price", "quantity"
        ]

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id', 'items', 'total_price'
        ]

    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "address", "phone", "comment"]

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        cart = getattr(user, "cart", None)
        if not cart or not cart.items.exists():
            raise serializers.ValidationError("Корзина пустая!")

        order = Order.objects.create(user=user, **validated_data)

        items = cart.items.select_related("product")
        for ci in items:
            OrderItem.objects.create(
                order=order,
                product=ci.product,
                price=ci.product.price,
                quantity=ci.quantity
            )

        cart.items.all().delete()
        return order

User = get_user_model()


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь не найден")
        return value

    def save(self):
        email = self.validated_data["email"]
        user = User.objects.get(email=email)

        code = PasswordResetCode.generate_code()

        PasswordResetCode.objects.create(
            user=user,
            code=code
        )

        send_mail(
            subject="Сброс пароля",
            message=f"Ваш код для сброса пароля: {code}",
            from_email=None,
            recipient_list=[email],
        )


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs["email"]
        code = attrs["code"]

        try:
            user = User.objects.get(email=email)
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code
            ).latest("created_at")
        except PasswordResetCode.DoesNotExist:
            raise serializers.ValidationError("Неверный код")

        if reset_code.is_expired():
            raise serializers.ValidationError("Код истек")

        return attrs


class SetNewPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(min_length=6)

    def validate(self, attrs):
        email = attrs["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        new_password = self.validated_data["new_password"]

        user.set_password(new_password)
        user.save()