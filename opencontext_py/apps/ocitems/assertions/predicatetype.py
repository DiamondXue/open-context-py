import hashlib
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.predicates.manage import PredicateManage
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


class PredicateTypeAssertions():
    """ Class for managing data_types for predicates, make sure consistency in data types
        used for predicates across manifest, predicate, and assertions tables
    """

    def __init__(self):
        self.alt_data_type = "xsd:string"  # data-type for predicates created from others
                                           # with inconsistent types

    def seperate_inconsistent_data_type(self, predicate_uuid):
        """ This looks for assertions that have different object types than the
            required main data_type of a given predicate. If such different assertions
            are found, the offending assertion is deleted and replaced by a new predicate
            and that new predicate is related back to the old predicate via 'skos:related'
        """
        plabel = False
        ptype = False
        pdata_type = False
        new_rel_predicates = []  # list of new predicates made from old
        try:
            pman = Manifest.objects.get(uuid=predicate_uuid)
            plabel = pman.label
            ptype = pman.class_uri
        except Manifest.DoesNotExist:
            pman = False
        try:  # look for the predicate item
            pred = Predicate.objects.get(uuid=predicate_uuid)
            pdata_type = pred.data_type
        except Predicate.DoesNotExist:
            pred = False
        if(plabel is not False
           and ptype is not False
           and pdata_type is not False):
            adistinct = Assertion.objects.filter(predicate_uuid=predicate_uuid)\
                                 .exclude(object_type=pdata_type)\
                                 .order_by('object_type')\
                                 .distinct('object_type')  # get distinct list of object_types
            for aitem in adistinct:  # list of assertions that are not using the good data type
                pm = PredicateManage()
                pm.source_id = pman.source_id
                pm.project_uuid = pman.project_uuid
                pm.sort = pred.sort
                cpred = pm.get_make_predicate(plabel, ptype, aitem.object_type)
                if(cpred is not False):
                    if(cpred.uuid not in new_rel_predicates):
                        new_rel_predicates.append(cpred.uuid)
            if(len(new_rel_predicates) > 0):
                #  add annotations storing the relationship between the new predicates and the old
                print('---- New predicates: ' + str(len(new_rel_predicates)))
                for new_pred_uuid in new_rel_predicates:
                    print('New predicate: ' + str(new_pred_uuid))
                    la = LinkAnnotation()
                    la.subject = new_pred_uuid
                    la.subject_type = 'predicates'
                    la.project_uuid = pman.project_uuid
                    la.source_id = pman.source_id
                    la.predicate_uri = 'skos:related'
                    la.object_uri = URImanagement.make_oc_uri(predicate_uuid, 'predicates')
                    la.save()
                alist = Assertion.objects.filter(predicate_uuid=predicate_uuid).exclude(object_type=pdata_type)
                for aitem in alist:  # list of assertions that are not using the good data type
                    pm = PredicateManage()
                    pm.source_id = pman.source_id
                    pm.project_uuid = pman.project_uuid
                    pm.sort = pred.sort
                    cpred = pm.get_make_predicate(plabel, ptype, aitem.object_type)
                    if(cpred is not False):
                        if(cpred.uuid not in new_rel_predicates):
                            new_rel_predicates.append(cpred.uuid)
                        Assertion.objects.filter(hash_id=aitem.hash_id).delete()
                        # delete the old instance of the assertion
                        aitem.predicate_uuid = cpred.uuid  # change the predicate to the new predicate
                        aitem.save()  # save the assertion with the new predicate
            else:
                print('--OK Predicate--: ' + str(predicate_uuid))

    def fix_inconsistent_data_types(self, data_type):
        """ fixes all predicates of a certain data_type and separates
           out assertions that have object_types that are different.
        """
        plist = Predicate.objects.filter(data_type=data_type)
        print('Predicate count: ' + str(len(plist)))
        for pitem in plist:
            print('Predicate: ' + pitem.uuid)
            self.seperate_inconsistent_data_type(pitem.uuid)

    def fix_all_inconsistent_data_types(self):
        """ fixes all predicates so that assertions have the correct object_type
           matching the data_type of the predicate """
        data_types = ['xsd:integer', 'xsd:double', 'xsd:date', 'xsd:boolean']
        for data_type in data_types:
            print('DATA-TYPE: ' + data_type)
            self.fix_inconsistent_data_types(data_type)
