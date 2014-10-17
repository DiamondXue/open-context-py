import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fields.describe import ImportFieldDescribe
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the imports fields annotations index.")


def view(request, source_id):
    """ Returns JSON data for an identifier in its hierarchy """
    ip = ImportProfile(source_id)
    if ip.project_uuid is not False:
        ip.get_field_annotations()
        anno_list = ip.jsonify_field_annotations()
        json_output = json.dumps(anno_list,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


def delete(request, source_id, annotation_id):
    """ Returns JSON data for an identifier in its hierarchy """
    if request.method == 'POST':
        ip = ImportProfile(source_id)
        if ip.project_uuid is not False:
            ifd = ImportFieldDescribe(source_id)
            ifd.delete_field_annotation(annotation_id)
            ip.get_field_annotations()
            anno_list = ip.jsonify_field_annotations()
            json_output = json.dumps(anno_list,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8')
        else:
            raise Http404
    else:
        return HttpResponseForbidden
