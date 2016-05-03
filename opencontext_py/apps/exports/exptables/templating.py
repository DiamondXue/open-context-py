import json
import time
from unidecode import unidecode
from django.conf import settings
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.filemath import FileMath
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable


class ExpTableTemplating():
    """
    Methods for making metadata templates for a table
    """

    def __init__(self, table_id):
        self.nav_items = settings.NAV_ITEMS
        self.act_nav = 'tables'
        self.public_table_id = table_id
        if '/' in table_id:
            id_ex = table_id.split('/')
            table_id = id_ex[1] + '_' + id_ex[0]
        self.table_id = table_id
        self.exp_tab = self.get_exp_table_obj(table_id)
        self.uuid = table_id  # for template
        self.project_uuid = table_id  # for template
        self.view_permitted = True
        self.csv_url = False
        self.csv_size_human = False
        self.old_csv_files = []
        self.cite_year = False
        self.cite_released = False
        self.cite_updated = False
        self.cite_authors = ''
        self.cite_editors = ''
        self.cite_projects = ''
        self.doi = False
        self.ark = False
        self.cite_uri = URImanagement.make_oc_uri(self.public_table_id, 'tables')
        self.template_fields = []
        self.sample_rows = []

    def get_exp_table_obj(self, table_id):
        """ gets an export table model object
            or returns false if it does not exist
        """
        try:
            exp_tab = ExpTable.objects.get(table_id=table_id)
        except ExpTable.DoesNotExist:
            exp_tab = False
        return exp_tab

    def prep_html(self):
        """ preps HTML data """
        if self.exp_tab is not False:
            json_ld = self.make_json_ld()
            self.get_csv_url(json_ld)
            self.get_old_csv_files(json_ld)
            self.make_cite_authors(json_ld)
            self.make_cite_editors(json_ld)
            self.make_cite_time(json_ld)
            self.make_cite_projects(json_ld)
            self.make_template_field_list(json_ld)
            self.make_sample_records(1, 100)

    def prep_csv(self):
        """ preps CSV data """
        if self.exp_tab is not False:
            json_ld = self.make_json_ld()
            self.get_csv_url(json_ld)

    def make_json_ld(self):
        """ makes a JSON-LD object for the table metadata

            Need oc-table namespace
            need to include the cc-rel namespace

            need to add this name space
            http://www.w3.org/2003/01/geo/ as geo:lat, geo:lon
        """
        json_ld = LastUpdatedOrderedDict()
        if self.exp_tab is not False:
            json_ld['id'] = URImanagement.make_oc_uri(self.public_table_id, 'tables')
            json_ld['label'] = self.exp_tab.label
            json_ld['fields'] = self.exp_tab.field_count
            json_ld['rows'] = self.exp_tab.row_count
            json_ld['dc-terms:issued'] = self.exp_tab.created.date().isoformat()
            json_ld['dc-terms:modified'] = self.exp_tab.updated.date().isoformat()
            json_ld['has-fields'] = self.get_field_list()
            for key, objects in self.exp_tab.meta_json.items():
                json_ld[key] = objects
        return json_ld

    def make_cite_time(self, json_ld):
        """ makes attributes used for citation purposes (time) """
        if 'dc-terms:issued' in json_ld:
            self.cite_year = json_ld['dc-terms:issued'][:4]
            self.cite_released = json_ld['dc-terms:issued']
        if 'dc-terms:modified' in json_ld:
            self.cite_updated = json_ld['dc-terms:modified']

    def make_cite_projects(self, json_ld):
        """ makes a string for citation of projects """
        projects_list = []
        if 'dc-terms:source' in json_ld:
            for item in json_ld['dc-terms:source']:
                projects_list.append(item['label'])
        self.cite_projects = ', '.join(projects_list)
        return self.cite_projects

    def get_field_list(self):
        """ gets a list of fields used with the current table """
        field_list = []
        ex_fields = ExpField.objects\
                            .filter(table_id=self.table_id)\
                            .order_by('field_num')
        for ex_field in ex_fields:
            field = LastUpdatedOrderedDict()
            field['id'] = '#field-' + str(ex_field.field_num)
            field['label'] = ex_field.label
            for key, objects in ex_field.rel_ids.items():
                field[key] = objects
            field_list.append(field)
        return field_list

    def make_template_field_list(self, json_ld):
        """ makes a field_list easy html templating """
        # rel preds are where we look for related URIs to
        # that will have links for more information about a field
        rel_preds = ['rdfs:isDefinedBy',
                     'oc-tab:equiv-uri',
                     'oc-tab:equiv-label']
        if 'has-fields' in json_ld:
            raw_field_list = json_ld['has-fields']
        else:
            raw_field_list = self.get_field_list()
        template_fields = []
        for raw_field in raw_field_list:
            uris = []
            for rel_pred in rel_preds:
                if rel_pred in raw_field:
                    obj = raw_field[rel_pred]
                    if len(obj) > 8:
                        if obj[:7] == 'http://' or \
                           obj[:8] == 'https://':
                            uri_item = {'predicates': False,
                                        'uri': obj}
                            uris.append(uri_item)
                        elif obj[:8] == 'oc-pred:':
                            uri_item = {'predicates': obj.replace('oc-pred:', ''),
                                        'uri': False}
                            uris.append(uri_item)
            raw_field['uris'] = uris
            template_fields.append(raw_field)
        self.template_fields = template_fields
        return self.template_fields

    def get_csv_url(self, json_ld):
        """ gets the csv link from the json-ld """
        if ExpTable.PREDICATE_DUMP in json_ld:
            for item in json_ld[ExpTable.PREDICATE_DUMP]:
                if 'text/csv' in item['dc-terms:hasFormat'] and \
                   'dc-terms:isReplacedBy' not in item:
                    # this is the current item, since it does not
                    # have a "replaced-by" predicate
                    self.csv_url = item['id']
                    fmath = FileMath()
                    self.csv_size_human = fmath.approximate_size(float(item['dcat:size']))
                    break
        return self.csv_url

    def get_old_csv_files(self, json_ld):
        """ gets the url for an old versions of CSV dumps of the data """
        if ExpTable.PREDICATE_DUMP in json_ld:
            for item in json_ld[ExpTable.PREDICATE_DUMP]:
                if 'text/csv' in item['dc-terms:hasFormat'] and \
                   'dc-terms:isReplacedBy' in item:
                    # this is an old item, since it has
                    # a "replaced-by" predicate
                    fmath = FileMath()
                    item['size-human'] = fmath.approximate_size(float(item['dcat:size']))
                    self.old_csv_files.append(item)

    def make_cite_authors(self, json_ld):
        """ makes a string listing the authors for citation """
        row_count = self.exp_tab.row_count
        min_author_count = row_count * .01  # contribute at least 10% to be an author
        w_author_tups = []
        if 'dc-terms:contributor' in json_ld:
            raw_authors = json_ld['dc-terms:contributor']
        elif 'dc-terms:creator' in json_ld:
            raw_authors = json_ld['dc-terms:creator']
        else:
            raw_authors = []
        final_author_list = []
        sorted_author_tuples = self.make_consolidated_person_tuples(raw_authors)
        for s_tup in sorted_author_tuples:
            if s_tup[1] >= min_author_count or len(final_author_list) <= 10:
                final_author_list.append(s_tup[0])
        self.cite_authors = ', '.join(final_author_list)
        return self.cite_authors

    def make_cite_editors(self, json_ld):
        """ makes a string listing editors for citation """
        row_count = self.exp_tab.row_count
        min_ed_count = row_count * .005  # contribute at least 5% to be an editor
        if 'dc-terms:creator' in json_ld:
            raw_editors = json_ld['dc-terms:creator']
        else:
            raw_editors = []
        final_editor_list = []
        sorted_ed_tuples = self.make_consolidated_person_tuples(raw_editors)
        for s_tup in sorted_ed_tuples:
            if s_tup[1] >= min_ed_count or len(final_editor_list) <= 10:
                final_editor_list.append(s_tup[0])
        self.cite_editors = ', '.join(final_editor_list)
        return self.cite_editors

    def make_consolidated_person_tuples(self, raw_person_list):
        """ makes a consolidated list of persons
            as tuples of (name, count)
            in order to consolidate people with the same
            name but different URIs (poorly reconciled entities)
        """
        consolidated_ids = []
        consolidated_tuple_list = []
        look_person_list = raw_person_list
        last_count = self.exp_tab.row_count
        for raw_person in raw_person_list:
            # print('ID consolidated: ' + str(len(consolidated_ids)))
            if 'count' in raw_person:
                count = float(raw_person['count'])
            else:
                count = last_count
            last_count = count
            act_name = raw_person['label']
            act_uniname = unidecode(act_name)
            act_id = raw_person['id']
            for look_person in look_person_list:
                look_id = look_person['id']
                if look_id != act_id and \
                   look_id not in consolidated_ids and \
                   (act_name == look_person['label'] or act_uniname == unidecode(look_person['label'])):
                    # same name but different record for a person,
                    # lets consolidate it
                    consolidated_ids.append(look_person['id'])
                    count += float(look_person['count'])
            if act_id not in consolidated_ids:
                # print('Adding ' + str(unidecode(act_name)))
                person_tuple = (act_name, count)
                consolidated_tuple_list.append(person_tuple)
                consolidated_ids.append(act_id)
        # now sort the tuples in descending order of counts
        sorted_person_tuples = sorted(consolidated_tuple_list,
                                      key=lambda x: x[1],
                                      reverse=True)
        return sorted_person_tuples

    def make_sample_records(self, start_row, end_row):
        """ makes sample records for a given table """
        row_nums = []
        rows = LastUpdatedOrderedDict()
        exp_cells = ExpCell.objects\
                           .filter(table_id=self.table_id,
                                   row_num__gte=start_row,
                                   row_num__lte=end_row)
        for exp_cell in exp_cells:
            if exp_cell.row_num not in row_nums:
                # now start out with a dict for a blank string
                # for each field expected in the row
                row_nums.append(exp_cell.row_num)
                field_vals = LastUpdatedOrderedDict()
                field_num = 1
                while field_num <= self.exp_tab.field_count:
                    field_vals[field_num] = ''
                    field_num += 1
                rows[exp_cell.row_num] = field_vals
            record = self.html_format_record(exp_cell.record)
            rows[exp_cell.row_num][exp_cell.field_num] = record
        sample_rows = []
        for row_num in row_nums:
            sample_recs = []
            field_num = 1
            while field_num <= self.exp_tab.field_count:
                sample_recs.append(rows[row_num][field_num])
                field_num += 1
            sample_rows.append(sample_recs)
        self.sample_rows = sample_rows
        return self.sample_rows

    def html_format_record(self, record):
        """ adds html formatting to a record, including putting
            URIs into <a> tags
        """
        output = record
        if '; ' in record:
            rec_ex = record.split('; ')
        else:
            rec_ex = [record]
        change = False
        new_parts = []
        for rec_part in rec_ex:
            if rec_part[:7] == 'http://' or \
               rec_part[:8] == 'https://':
                # put this into a link
                change = True
                new_part = '<a href="' + rec_part + '" target="_blank">'
                new_part += rec_part + '</a>'
                new_parts.append(new_part)
            else:
                num_part_trim = False
                try:
                    num_str = float(rec_part)
                except:
                    num_str = False
                if num_str is not False:
                    num_part_trim = self.trim_trailing_zeros(rec_part)
                if num_part_trim is not False:
                    change = True
                    new_parts.append(num_part_trim)
                else:
                    new_parts.append(rec_part)
        if change:
            output = '; '.join(new_parts)
        return output

    def trim_trailing_zeros(self, num_str):
        """ trim trailing zeros that make a number
            seem like it has too much precision
        """
        trim_out = num_str
        str_len = len(num_str)
        if str_len > 4:
            cont = True
            while cont:
                # print('Checking: ' + trim_out)
                act_char = trim_out[-1]
                str_len = len(trim_out)
                if str_len <= 4:
                    cont = False
                if act_char == '0' and cont:
                    str_len = len(trim_out)
                    trim_out = trim_out[0:(str_len - 1)]
                    cont = True
                else:
                    cont = False
        return trim_out
