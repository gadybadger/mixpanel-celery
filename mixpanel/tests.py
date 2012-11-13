from __future__ import absolute_import

from celery.exceptions import RetryTaskError
from django.utils import simplejson
import base64
import unittest
import urllib

from . import tasks
from .conf import settings as mp_settings

class EventTrackerTest(unittest.TestCase):
    def setUp(self):
        mp_settings.MIXPANEL_API_TOKEN = 'testtesttest'
        mp_settings.MIXPANEL_API_SERVER = 'api.mixpanel.com'
        mp_settings.MIXPANEL_TRACKING_ENDPOINT = '/track/'

    def test_handle_properties_w_token(self):
        properties = tasks._handle_properties({}, 'foo')
        self.assertEqual('foo', properties['token'])

    def test_handle_properties_no_token(self):
        mp_settings.MIXPANEL_API_TOKEN = 'bar'

        properties = tasks._handle_properties({}, None)
        self.assertEqual('bar', properties['token'])

    def test_handle_properties_empty(self):
        mp_settings.MIXPANEL_API_TOKEN = 'bar'

        properties = tasks._handle_properties(None, None)
        self.assertEqual('bar', properties['token'])

    def test_handle_properties_given(self):

        properties = tasks._handle_properties({'token': 'bar'}, None)
        self.assertEqual('bar', properties['token'])

        properties = tasks._handle_properties({'token': 'bar'}, 'foo')
        self.assertEqual('bar', properties['token'])

    def test_build_params(self):
        event = 'foo_event'
        properties = {'token': 'testtoken'}
        params = {'event': event, 'properties': properties}

        url_params = tasks._build_params(event, properties)

        expected_params = urllib.urlencode({
            'data':base64.b64encode(simplejson.dumps(params)),
        })

        self.assertEqual(expected_params, url_params)

    def test_failed_request(self):
        mp_settings.MIXPANEL_TRACKING_ENDPOINT = 'brokenurl'

        self.assertRaises(RetryTaskError,
                          tasks.event_tracker,
                          'event_foo', throw_retry_error=True)

    def test_failed_socket_request(self):
        mp_settings.MIXPANEL_API_SERVER = '127.0.0.1:60000'

        self.assertRaises(RetryTaskError,
                          tasks.event_tracker,
                          'event_foo', throw_retry_error=True)


    def test_run(self):
        # "correct" result obtained from: http://mixpanel.com/api/docs/console
        result = tasks.event_tracker('event_foo', {})

        self.assertTrue(result)

    def test_old_run(self):
        """non-recorded events should return False"""
        # Times older than 3 hours don't get recorded according to: http://mixpanel.com/api/docs/specification
        # equests will be rejected that are 3 hours older than present time
        result = tasks.event_tracker('event_foo', {'time': 1245613885})

        self.assertFalse(result)

    def test_debug_logger(self):
        result = tasks.event_tracker('event_foo', {})

        self.assertTrue(result)

class FunnelEventTrackerTest(unittest.TestCase):
    def setUp(self):
        mp_settings.MIXPANEL_API_TOKEN = 'testtesttest'
        mp_settings.MIXPANEL_API_SERVER = 'api.mixpanel.com'
        mp_settings.MIXPANEL_TRACKING_ENDPOINT = '/track/'

    def test_afp_validation(self):

        funnel = 'test_funnel'
        step = 'test_step'
        goal = 'test_goal'

        # neither
        properties = {}
        self.assertRaises(tasks.InvalidFunnelProperties,
                          tasks._add_funnel_properties,
                          properties, funnel, step, goal)

        # only distinct
        properties = {'distinct_id': 'test_distinct_id'}
        fp = tasks._add_funnel_properties(properties, funnel, step, goal)

        # only ip
        properties = {'ip': 'some_ip'}
        self.assertRaises(tasks.InvalidFunnelProperties,
                          tasks._add_funnel_properties,
                          properties, funnel, step, goal)

        # both
        properties = {'distinct_id': 'test_distinct_id',
                      'ip': 'some_ip'}
        fp = tasks._add_funnel_properties(properties, funnel, step, goal)

    def test_afp_properties(self):

        funnel = 'test_funnel'
        step = 'test_step'
        goal = 'test_goal'

        properties = {'distinct_id': 'test_distinct_id'}

        funnel_properties = tasks._add_funnel_properties(properties, funnel,
                                                       step, goal)

        self.assertEqual(funnel_properties['funnel'], funnel)
        self.assertEqual(funnel_properties['step'], step)
        self.assertEqual(funnel_properties['goal'], goal)

    def test_run(self):
        funnel = 'test_funnel'
        step = 'test_step'
        goal = 'test_goal'

        result = tasks.funnel_event_tracker(funnel, step, goal, {'distinct_id': 'test_user'})

        self.assertTrue(result)
