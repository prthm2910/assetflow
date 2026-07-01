"""
apps/core/organizations/serializers.py — Serializers for Organization and OrganizationConfig.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.core.organizations.models import Organization, OrganizationConfig


User = get_user_model()


class OrganizationConfigSerializer(BaseSerializer):
    """Serializer for OrganizationConfig (read-only on org_id, writable on settings)."""

    organization_id = serializers.CharField(source="organization.org_id", read_only=True)

    class Meta:
        model = OrganizationConfig
        fields = [
            "organization_id",
            "admin_user",
            "default_timezone",
            "working_hours_start",
            "working_hours_end",
            "working_days",
            "asset_code_prefix",
            "request_approval_required",
            "auto_approve_requests",
            "max_requests_per_month",
            "notify_on_asset_allocated",
            "notify_on_asset_returned",
            "notify_on_request_submitted",
            "notify_on_request_approved",
            "notify_on_request_rejected",
            "notify_on_incident_reported",
            "notify_on_incident_resolved",
        ]
        read_only_fields = [
            "organization_id",
        ]

    def validate_admin_user(self, value):
        """Ensure admin_user belongs to this organization (cross-tenant prevention)."""
        if value is None:
            return value
        if self.instance:
            org = self.instance.organization
            if value.organization != org:
                raise serializers.ValidationError(
                    "The designated admin user must belong to this organization."
                )
        return value

    def validate_default_timezone(self, value):
        """Validate IANA timezone string."""
        import zoneinfo

        try:
            zoneinfo.ZoneInfo(value)
        except Exception:
            raise serializers.ValidationError("Invalid IANA timezone string.")
        return value


class OrganizationSerializer(BaseSerializer):
    """
    Full organization serializer — super admin CRUD operations.
    Exposes org_id, config nested, logo, all status fields.
    """

    config = OrganizationConfigSerializer(read_only=True)
    config_data = OrganizationConfigSerializer(write_only=True, required=False)

    class Meta:
        model = Organization
        fields = [
            "org_id",
            "name",
            "slug",
            "description",
            "contact_email",
            "contact_phone",
            "address",
            "city",
            "country",
            "logo",
            "config",
            "config_data",
        ]
        read_only_fields = [
            "org_id",
        ]

    def create(self, validated_data):
        # config_data is handled via config nested serializer on the model save()
        # Organization.save() auto-creates config on first save
        config_data = validated_data.pop("config_data", None)
        organization = Organization.objects.create(**validated_data)
        if config_data:
            config = getattr(organization, "config", None)
            if config:
                for attr, value in config_data.items():
                    setattr(config, attr, value)
                config.save()
        return organization

    def update(self, instance, validated_data):
        config_data = validated_data.pop("config_data", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if config_data:
            config = getattr(instance, "config", None)
            if config:
                for attr, value in config_data.items():
                    setattr(config, attr, value)
                config.save()
            else:
                OrganizationConfig.objects.create(
                    organization=instance,
                    **config_data,
                )
        return instance


class OrganizationListSerializer(BaseSerializer):
    """Lightweight serializer for list views — no nested config."""

    class Meta:
        model = Organization
        fields = [
            "org_id",
            "name",
            "slug",
            "contact_email",
            "city",
            "country",
        ]


class OrganizationProfileSerializer(BaseSerializer):
    """
    Organization profile serializer — what any org member sees for their own org.
    Includes nested config for profile page display.
    """

    config = OrganizationConfigSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "org_id",
            "name",
            "slug",
            "description",
            "contact_email",
            "contact_phone",
            "address",
            "city",
            "country",
            "logo",
            "config",
        ]
        read_only_fields = [
            "org_id",
            "slug",
        ]
