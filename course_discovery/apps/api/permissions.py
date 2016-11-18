from edx_rest_framework_extensions import permissions
from rest_framework_jwt.authentication import BaseJSONWebTokenAuthentication


class JwtScopePermissions(permissions.BasePermission):
    ALL_ACTION = 'all'

    ACTION_MAP = {
        'GET': 'read',
        'OPTIONS': 'read',
        'HEAD': 'read',
        'POST': 'write',
        'PUT': 'write',
        'PATCH': 'write',
        'DELETE': 'write',
    }

    def get_resource(self, view):
        resource = getattr(view, 'scope_resource', None)

        if not resource:
            serializer_class = view.get_serializer_class()
            resource = serializer_class.Meta.model.__name__.lower()

        return resource

    def has_permission(self, request, view):
        # NOTE: These permissions only apply when using JWT authentication. This allows us to
        # support both JWT and session authentication.
        if not isinstance(request.successful_authenticator, BaseJSONWebTokenAuthentication):
            return True

        token = request.auth
        if not token:
            return False

        token_scopes = set(token.get('scopes', []))
        if not token_scopes:
            return False

        required_scopes = set(self.get_required_scopes(request, view))
        return bool(required_scopes.intersection(token_scopes))

    def get_required_scopes(self, request, view):
        resource = self.get_resource(view)
        actions = [self.ALL_ACTION, self.ACTION_MAP[request.method]]
        return ['{resource}:{action}'.format(resource=resource, action=action) for action in actions]

# TEST CODE
# from time import time
#
# import jwt
# from edx_rest_api_client.client import EdxRestApiClient
#
# now = int(time())
# expires_in = 3600
# secret = 'lms-secret'
#
# payload = {
#     'aud': 'lms-key',
#     'exp': now + expires_in,
#     'iat': now,
#     'iss': 'http://127.0.0.1:8000/oauth2',
#     'preferred_username': 'edx',
#     'scopes': ['catalog:read', 'catalog:write'],
#     'sub': '1234',
# }
#
# token = jwt.encode(payload, secret).decode('utf-8')
# print(token)
#
# client = EdxRestApiClient('http://cd.local:8008/api/v1/', jwt=token)
# print(client.catalogs.get())
# print(client.catalogs.post({}))
