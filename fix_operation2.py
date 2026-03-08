python - << 'EOF'
import re, shutil

path = 'pos_backend/sales/serializers.py'
shutil.copy2(path, path + '.bak')

with open(path, encoding='utf-8') as f:
    content = f.read()

OLD = '''class SaleListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    items_count = serializers.ReadOnlyField()

    class Meta:
        model = Sale
        fields = [
            'id', 'customer_name', 'user_name', 'total',
            'payment_method', 'status', 'items_count', 'created_at'
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'غير محدد\''''

NEW = '''class SaleListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    user_name     = serializers.SerializerMethodField()
    items_count   = serializers.ReadOnlyField()
    has_returns   = serializers.SerializerMethodField()
    returns_count = serializers.SerializerMethodField()

    class Meta:
        model  = Sale
        fields = [
            'id', 'invoice_number', 'customer_name', 'user_name',
            'total', 'payment_method', 'status',
            'items_count', 'has_returns', 'returns_count', 'created_at'
        ]

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'غير محدد'

    def get_has_returns(self, obj):
        return obj.returns.exists()

    def get_returns_count(self, obj):
        return obj.returns.count()'''

if OLD in content:
    content = content.replace(OLD, NEW)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ تم التعديل بنجاح')
else:
    print('⚠️  النص القديم مش موجود — عدّل يدوياً')
EOF
