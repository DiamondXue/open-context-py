import copy
import json
import logging
import time
from datetime import datetime
from django.conf import settings
from mysolr.compat import urljoin, compat_args, parse_response
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchfilters import SearchFilters
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


class SolrResult():

    def __init__(self, request_dict=None, base_search_url='/search/'):
        self.json_ld = LastUpdatedOrderedDict()
        self.request_dict = copy.deepcopy(request_dict)
        self.base_search_url = base_search_url
        self.id = None
        self.act_responses = []
    

    # -----------------------------------------------------------------
    # Methods to make geneal response metadata
    # -----------------------------------------------------------------
    def make_response_id(self):
        """Makes the ID for the response JSON-LD"""
        # NOTE: The order of the URL parameters will be predicable
        # to help normalize search IDs.
        if self.id:
            return self.id
        sl = SearchLinks(
            request_dict=self.request_dict,
            base_search_url=self.base_search_url
        )
        urls = sl.make_urls_from_request_dict()
        self.id = urls['html']
        return self.id


    def add_publishing_datetime_metadata(self, solr_json, default_to_current=True):
        """Adds publishing modified and created metadata to the response JSON-LD"""
        # NOTE: Solr already defaults to representing time in 
        # ISO 8601, so we're just pulling the appropriate time
        # info from the solr_json to metadata fields in our response
        # JSON-LD.
        meta_configs = [
            (
                # Last modified.
                'dcmi:modified',
                [
                    'stats', 
                    'stats_fields',
                    'updated',
                    'max',
                ],
            ),
            (
                # Last published
                'dcmi:created',
                [
                    'stats', 
                    'stats_fields',
                    'published',
                    'max',
                ],
            ),
            (
                # Earliest published
                'oai-pmh:earliestDatestamp',
                [
                    'stats', 
                    'stats_fields',
                    'published',
                    'min',
                ],
            ),
        ]
        for json_ld_key, path_keys_list in meta_configs:
            act_time = utilities.get_dict_path_value(
                path_keys_list, 
                solr_json
            )
            if not act_time:
                # We could not find the time object.
                if not default_to_current:
                    # Skip, since we're not to default to 
                    # the current time.
                    continue
                # Add ISO 8601 current time for the missing value.
                act_time = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
            self.json_ld[json_ld_key] = act_time 


    def add_form_use_life_date_range(self, solr_json, iso_year_format=True):
        """Adds earliest and latest form-use-life dates"""
        meta_configs = [
            (
                # Earliest date items formed, used, or alive.
                'start',
                [
                    'stats', 
                    'stats_fields',
                    'form_use_life_chrono_earliest',
                    'min',
                ],
            ),
            (
                # Latest date items formed, used, or alive
                'stop',
                [
                    'stats', 
                    'stats_fields',
                    'form_use_life_chrono_latest',
                    'max',
                ],
            ),
        ]
        for json_ld_key, path_keys_list in meta_configs:
            act_date = utilities.get_dict_path_value(
                path_keys_list, 
                solr_json
            )
            if iso_year_format and act_date is not None:
                act_date = ISOyears().make_iso_from_float(act_date)
            self.json_ld[json_ld_key] = act_date


    # -----------------------------------------------------------------
    # Methods to make links for paging + sorting navigation 
    # -----------------------------------------------------------------
    def _make_paging_links(self, start, rows, act_request_dict):
        """Makes links for paging for start rows from a request dict"""
        start = str(int(start))
        rows = str(rows)

        # Remove previously set parameters relating to paging.
        for param in ['start', 'rows']:
            if param in act_request_dict:
                act_request_dict.pop(param, None)

        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        sl.add_param_value('start', start)
        sl.add_param_value('rows', rows)
        urls = sl.make_urls_from_request_dict()
        return urls


    def add_paging_json(self, solr_json):
        """ Adds JSON for paging through results """
        
        # The total found (numFound) is in the solr response.
        total_found = utilities.get_dict_path_value(
            ['response', 'numFound'],
            solr_json
        )

        # Start and rows comes from the responseHeader
        start = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'start'],
            solr_json
        )
        rows = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'rows'],
            solr_json
        )
        if (total_found is None
            or start is None
            or rows is None):
            return None
        
        # Add number found, start index, paging
        # information about this search result.
        total_found = int(float(total_found))
        start = int(float(start))
        rows = int(float(rows))
        self.json_ld['totalResults'] = total_found
        self.json_ld['startIndex'] = start
        self.json_ld['itemsPerPage'] = rows
        
        # start off with a the request dict, then
        # remove 'start' and 'rows' parameters
        act_request_dict = copy.deepcopy(self.request_dict)
        if 'start' in act_request_dict:
            act_request_dict.pop('start', None)
        if 'rows' in act_request_dict:
            act_request_dict.pop('rows', None)

        # add a first page link
        if start > 0:
            links = self._make_paging_links(
                start=0,
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['first'] = links['html']
            self.json_ld['first-json'] = links['json']
        if start >= rows:
            # add a previous page link
            links = self._make_paging_links(
                start=(start - rows),
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['previous'] = links['html']
            self.json_ld['previous-json'] = links['json']
        if start + rows < total_found:
            # add a next page link
            print('Here: {}'.format(str(act_request_dict)))
            links = self._make_paging_links(
                start=(start + rows),
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['next'] = links['html']
            self.json_ld['next-json'] = links['json']
        num_pages = round(total_found / rows, 0)
        if num_pages * rows >= total_found:
            num_pages -= 1
        # add a last page link
        links = self._make_paging_links(
            start=(num_pages * rows),
            rows=rows,
            act_request_dict=copy.deepcopy(act_request_dict)
        )
        self.json_ld['last'] = links['html']
        self.json_ld['last-json'] = links['json']
    

    def add_sorting_json(self):
        """Adds JSON to describe result sorting """
        # Deep copy the request dict to not mutate it.
        act_request_dict = copy.deepcopy(self.request_dict)
        sort_opts = SortingOptions(base_search_url=self.base_search_url)
        sort_opts.make_current_sorting_list(act_request_dict)
        # Add objects describing the currently active sorting.
        self.json_ld['oc-api:active-sorting'] = sort_opts.current_sorting
        act_request_dict = copy.deepcopy(self.request_dict)
        sort_links = sort_opts.make_sort_links_list(act_request_dict)
        # Add objects describing other sort options available.
        self.json_ld['oc-api:has-sorting'] = sort_links

    
    # -----------------------------------------------------------------
    # Methods to make active filters with links to remove or broaden 
    # -----------------------------------------------------------------
    def add_filters_json(self):
        """Adds JSON describing currently used query filters"""
        search_filters = SearchFilters(
            base_search_url=self.base_search_url
        )
        filters = search_filters.add_filters_json(self.request_dict)
        if len(filters) > 0:
            self.json_ld['oc-api:active-filters'] = filters


    def add_text_fields(self):
        """Adds general and project-specific property text query options """
        text_fields = []
        # first add a general key-word search option
        act_request_dict = copy.deepcopy(self.request_dict)
        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        raw_fulltext_search = utilities.get_request_param_value(
            act_request_dict, 
            param='q',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        field = LastUpdatedOrderedDict()
        field['id'] = '#textfield-keyword-search'
        field['label'] = configs.FILTER_TEXT_SEARCH_TITLE
        field['oc-api:search-term'] = raw_fulltext_search
        if not raw_fulltext_search:
            # No keyword search found in request, so
            # make a template for keyword searches.
            sl.add_param_value(
                'q', 
                configs.TEXT_URL_QUERY_TEMPLATE
            )
            urls = sl.make_urls_from_request_dict()
            field['oc-api:template'] = urls['html']
            field['oc-api:template-json'] = urls['json']
        else:
            # A keyword search was found, so make a
            # template for replacing it with another
            # keyword search.
            sl.replace_param_value(
                'q',
                match_old_value=raw_fulltext_search,
                new_value=configs.TEXT_URL_QUERY_TEMPLATE
            )
            urls = sl.make_urls_from_request_dict()
            field['oc-api:template'] = urls['html']
            field['oc-api:template-json'] = urls['json']
        text_fields.append(field)

        # NOTE This adds project specific property text
        # query options are listed in the search-filters

        # Add the text fields if they exist.
        if len(text_fields):
            self.json_ld['oc-api:has-text-search'] = text_fields
        return text_fields


    def create_result(self, solr_json):
        """Creates a solr result"""
        if 'metadata' in self.act_responses:
            self.json_ld['id'] = self.make_response_id()
            self.add_publishing_datetime_metadata(solr_json)
            self.add_form_use_life_date_range(solr_json)
            self.add_paging_json(solr_json)
            self.add_sorting_json()
            self.add_filters_json()
            self.add_text_fields()




    
    