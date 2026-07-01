from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination, CursorPagination


class MyPageNumberPaginations(PageNumberPagination):
    page_size = 2
    page_size_query_param = 'page'
    max_page_size = 2


class MyLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100


class MyCursorPagination(CursorPagination):
    page_size = 10
    ordering = 'created_at'


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
