from django.db import models


# Stores data about fields from imported tables
class ImportField(models.Model):

    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    is_keycell = models.BooleanField()
    ref_name = models.CharField(max_length=200, db_index=True)
    ref_orig_name = models.CharField(max_length=200)
    f_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imp_fields'
        ordering = ['source_id', 'field_num']
        unique_together = ('source_id', 'field_num')
