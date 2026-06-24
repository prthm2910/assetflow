"""
apps/base/serializers.py — Base serializer for all AssetFlow models.
"""

from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer for all AssetFlow models.
    Inherit from this in child serializers.
    """

    class Meta:
        abstract = True
