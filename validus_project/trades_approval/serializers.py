from rest_framework import serializers

class TradeDetailsSerializer(serializers.Serializer):
    tradingEntity     = serializers.CharField(max_length=120)
    counterparty      = serializers.CharField(max_length=120)
    direction         = serializers.ChoiceField(choices=["BUY", "SELL"])
    style             = serializers.CharField(max_length=20)

    notionalCurrency  = serializers.CharField(max_length=3)
    notionalAmount    = serializers.DecimalField(max_digits=20, decimal_places=2)

    underlying        = serializers.ListField(
        child=serializers.CharField(max_length=3),
        allow_empty=False
    )

    tradeDate         = serializers.DateField()
    valueDate         = serializers.DateField()
    deliveryDate      = serializers.DateField()

    def validate(self, data):
        unknown = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError({k: "Unknown field." for k in sorted(unknown)})
        return data

class TradeUpdateSerializer(serializers.Serializer):
    tradingEntity     = serializers.CharField(max_length=120, required=False)
    counterparty      = serializers.CharField(max_length=120, required=False)
    direction         = serializers.ChoiceField(choices=["BUY", "SELL"], required=False)
    style             = serializers.CharField(max_length=20, required=False)

    notionalCurrency  = serializers.CharField(max_length=3, required=False)
    notionalAmount    = serializers.DecimalField(max_digits=20, decimal_places=2, required=False)

    underlying = serializers.ListField(child=serializers.CharField(max_length=3),allow_empty=False,required=False)

    tradeDate         = serializers.DateField(required=False)
    valueDate         = serializers.DateField(required=False)
    deliveryDate      = serializers.DateField(required=False)

    def validate(self, data):
        unknown = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError(
                {k: "Unknown field." for k in sorted(unknown)}
            )

        provided = set(data.keys()) & set(self.fields.keys())
        if not provided:
            raise serializers.ValidationError(
                "Provide at least one updatable trade detail."
            )
        return data

class BookSerializer(serializers.Serializer):
    userId = serializers.CharField(max_length=64)
    strike = serializers.DecimalField(max_digits=20, decimal_places=6)

    def validate(self, data):
        unknown = set(self.initial_data.keys()) - set(self.fields.keys())
        if unknown:
            raise serializers.ValidationError({k: "Unknown field." for k in sorted(unknown)})
        return data

    def validate_strike(self, value):
        if value <= 0:
            raise serializers.ValidationError("strike must be greater than 0.")
        return value