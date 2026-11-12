from html.parser import HTMLParser
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tag_positions = []
        self.dialog_count = 0
        self.body_class = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tag_positions.append(tag)
        if tag == 'body':
            self.body_class = attrs.get('class', '')
        if attrs.get('id') == 'applicationResponseDialog':
            self.dialog_count += 1
            assert 'body' in self.tag_positions


class ApplicationTemplateTests(SimpleTestCase):
    def test_response_modal_only_occurs_once_inside_body(self):
        html = render_to_string('pages/my_applications.html', {'csrf_token': 'test'})
        parser = PageParser()
        parser.feed(html)
        self.assertEqual(parser.dialog_count, 1)
        self.assertEqual(parser.body_class, 'portal-home portal-applications')
        self.assertEqual(html.count('js/application-responses.js'), 1)
        self.assertNotIn('<dialog', html.split('</head>')[0])
