from edx_rest_framework_extensions import authentication
from rest_framework_jwt.authentication import jwt_decode_handler


class JwtAuthentication(authentication.JwtAuthentication):
    def authenticate(self, request):
        auth_tuple = super(JwtAuthentication, self).authenticate(request)
        if not auth_tuple:
            return None

        user, jwt_value = auth_tuple
        payload = jwt_decode_handler(jwt_value)
        return user, payload
