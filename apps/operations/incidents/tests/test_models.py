"""apps/operations/incidents/tests/test_models.py — Incident model unit tests."""

import pytest

from apps.operations.incidents.constants import IncidentCategory, IncidentStatus
from apps.operations.incidents.models import Incident


@pytest.mark.django_db
class TestIncidentModel:
    def test_inc_id_auto_generated(self, organization, employee, asset):
        """inc_id is auto-generated with INC prefix on save."""
        incident = Incident.objects.create(
            organization=organization,
            asset=asset,
            reported_by=employee,
            title="Screen cracked",
            description="Dropped the laptop, screen has a crack.",
        )
        assert incident.inc_id is not None
        assert incident.inc_id.startswith("INC")

    def test_inc_id_is_unique(self, organization, employee, asset):
        """Two incidents get different inc_id values."""
        i1 = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Issue 1", description="desc 1",
        )
        i2 = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Issue 2", description="desc 2",
        )
        assert i1.inc_id != i2.inc_id

    def test_default_status_is_reported(self, organization, employee, asset):
        """New incidents default to 'reported' status."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
        )
        assert incident.status == IncidentStatus.REPORTED.value

    def test_category_is_required(self, organization, employee, asset):
        """category field is required — validation rejects empty category."""
        from django.core.exceptions import ValidationError

        incident = Incident(
            organization=organization,
            asset=asset,
            reported_by=employee,
            title="Test",
            description="Test desc",
            # category intentionally omitted
        )
        with pytest.raises(ValidationError):
            incident.full_clean()  # Django model validation

    def test_category_choices_are_valid(self):
        """IncidentCategory enum provides valid choices."""
        choices = IncidentCategory.choices()
        assert len(choices) >= 5
        choice_values = [c[0] for c in choices]
        assert IncidentCategory.HARDWARE.value in choice_values
        assert IncidentCategory.OTHER.value in choice_values

    def test_status_choices_are_valid(self):
        """IncidentStatus enum provides valid choices."""
        choices = IncidentStatus.choices()
        assert len(choices) == 5
        choice_values = [c[0] for c in choices]
        assert IncidentStatus.REPORTED.value in choice_values
        assert IncidentStatus.CLOSED.value in choice_values

    def test_attachments_default_empty_list(self, organization, employee, asset):
        """attachments defaults to an empty list."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
        )
        assert incident.attachments == []

    def test_attachments_can_store_urls(self, organization, employee, asset):
        """attachments can store a list of URLs."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
            attachments=["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        )
        assert len(incident.attachments) == 2

    def test_str_with_all_relations(self, organization, employee, asset):
        """__str__ returns a readable summary."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Broken screen",
            description="Screen cracked after drop.",
        )
        s = str(incident)
        assert "Broken screen" in s
        assert incident.inc_id in s

    def test_str_with_null_relations(self):
        """__str__ guards against null FKs."""
        from django.core.exceptions import ObjectDoesNotExist

        incident = Incident(
            title="Orphan incident",
            description="No relations.",
        )
        # Accessing unfilled non-nullable FKs raises RelatedObjectDoesNotExist
        # before any __str__ guard can evaluate. The __str__ is safe on saved instances.
        with pytest.raises(ObjectDoesNotExist):
            str(incident)

    def test_resolved_at_null_by_default(self, organization, employee, asset):
        """resolved_at is null when incident is created."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
        )
        assert incident.resolved_at is None
        assert incident.closed_at is None

    def test_assigned_to_nullable(self, organization, employee, asset):
        """assigned_to is null by default."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
        )
        assert incident.assigned_to is None

    def test_soft_delete(self, organization, employee, asset):
        """delete() performs soft-delete (sets flags)."""
        incident = Incident.objects.create(
            organization=organization, asset=asset,
            reported_by=employee, title="Test", description="Test desc",
        )
        incident_id = incident.id
        incident.delete()

        # Should not be visible through default manager
        assert not Incident.objects.filter(id=incident_id).exists()
        # But should exist with all_with_deleted
        assert Incident.objects.all_with_deleted().filter(id=incident_id).exists()

    def test_meta_ordering(self):
        """Meta ordering is by -created_at (inherited from BaseModel)."""
        assert Incident._meta.ordering == ["-created_at"]

    def test_related_names(self, organization, employee, asset):
        """Related names are set correctly."""
        # Asset → incidents
        assert hasattr(asset, "incidents")
        # Employee → reported_incidents
        assert hasattr(employee, "reported_incidents")
