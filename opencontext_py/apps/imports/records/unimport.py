from django.db import models
from django.db.models import Q
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.imports.fields.templating import ImportProfile


# Removes the import of a from a source_id
class UnImport():

    def __init__(self, source_id, project_uuid):
        self.source_id = source_id
        self.project_uuid = project_uuid

    def delete_containment_assertions(self):
        """ Deletes containment assertions for an
            import
        """
        rem_assertions = Assertion.objects\
                                  .filter(source_id=self.source_id,
                                          project_uuid=self.project_uuid,
                                          subject_type='subjects',
                                          predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                          object_type='subjects')\
                                  .delete()

    def delete_describe_assertions(self):
        """ Deletes an import of description assertions
        """
        rem_assertions = Assertion.objects\
                                  .filter(source_id=self.source_id,
                                          project_uuid=self.project_uuid,
                                          object_type__in=ip.DEFAULT_DESCRIBE_OBJECT_TYPES)\
                                  .delete()

    def delete_predicate_vars(self):
        """ Deletes predicates that are variables
        """
        man_pred_vars = Manifest.objects\
                                .filter(source_id=self.source_id,
                                        project_uuid=self.project_uuid,
                                        item_type='predicates',
                                        class_uri='variable')
        for man_obj in man_pred_vars:
            rem_assertions = Assertion.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid,
                                              predicate_uuid=man_obj.uuid)\
                                      .delete()
            rem_pred = Predicate.objects\
                                .filter(source_id=self.source_id,
                                        project_uuid=self.project_uuid,
                                        uuid=man_obj.uuid)\
                                .delete()
            man_obj.delete()

    def delete_predicate_links(self):
        """ Deletes predicates that are links
        """
        man_pred_vars = Manifest.objects\
                                .filter(source_id=self.source_id,
                                        project_uuid=self.project_uuid,
                                        item_type='predicates',
                                        class_uri='link')
        for man_obj in man_pred_vars:
            rem_assertions = Assertion.objects\
                                      .filter(source_id=self.source_id,
                                              project_uuid=self.project_uuid,
                                              predicate_uuid=man_obj.uuid)\
                                      .delete()
            rem_pred = Predicate.objects\
                                .filter(source_id=self.source_id,
                                        project_uuid=self.project_uuid,
                                        uuid=man_obj.uuid)\
                                .delete()
            man_obj.delete()

    def delete_subjects_entities(self):
        """ Deletes subjects entities
            import
        """
         #get rid of "subjects" manifest records from this source
        rem_manifest = Manifest.objects\
                               .filter(source_id=self.source_id,
                                       project_uuid=self.project_uuid,
                                       item_type='subjects')\
                               .delete()
        #get rid of subject records from this source
        rem_subject = Subject.objects\
                             .filter(source_id=self.source_id,
                                     project_uuid=self.project_uuid)\
                             .delete()

    def delete_types_entities(self):
        """ Deletes types entities from an
            import
        """
         #get rid of "types" manifest records from this source
        rem_manifest = Manifest.objects\
                               .filter(source_id=self.source_id,
                                       project_uuid=self.project_uuid,
                                       item_type='types')\
                               .delete()
        #get rid of types records from this source
        rem_type = OCtype.objects\
                         .filter(source_id=self.source_id,
                                 project_uuid=self.project_uuid)\
                         .delete()

    def delete_strings(self):
        """ Deletes containment assertions for an
            import
        """
        rem_string = OCstring.objects\
                             .filter(source_id=self.source_id,
                                     project_uuid=self.project_uuid)\
                             .delete()
