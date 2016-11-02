#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Python Future imports
from __future__ import unicode_literals, absolute_import, print_function

# Python System imports
import re
from jinja2 import (Environment, ChoiceLoader, PackageLoader, FileSystemLoader,
                    TemplateNotFound)

from . import constants

# Templates must be named `<event name>.j2
# First search in the `event_templates` directory in the working directory,
# else fall back to the package defaults
jinja_env = Environment(loader=ChoiceLoader([
    FileSystemLoader('./event_templates'),
    PackageLoader('mattermost_gitlab', 'event_templates'),
    ]))


def markdown_quote(text):
    """Add Markdown quotes around a piece of text."""
    if not text:
        return ''
    return '> '.join(text.splitlines(True))


def escape_username(username):
    """Put zero-width spaces between every letter of user name.

    This will avoid generating mentions in Mattermost.
    """
    return '\u200b'.join(username)


def escape_mentions(text):
    if not text:
        return ''
    # Split the text on all mentions, and capture the mention.
    split_text = re.split(r'(@\w)', text)
    # every odd element in the split text is a mention.
    # Iterate over these and escape to prevent a mention
    for i, mention in enumerate(split_text[1::2]):
        split_text[2 * i + 1] = escape_username(mention)

    return ''.join(split_text)


def gitlab_url_from_repo(repo):
    return '/'.join(repo['homepage'].split('/')[:-2])


def gitlab_user_url(base_url, username):
        return '{}/u/{}'.format(base_url, username)


def raise_helper(msg):
    raise TemplateError(msg)


jinja_env.filters['markdown_quote'] = markdown_quote
jinja_env.filters['escape_username'] = escape_username
jinja_env.filters['escape_mentions'] = escape_mentions
jinja_env.filters['gitlab_url_from_repo'] = gitlab_url_from_repo
jinja_env.filters['gitlab_user_url'] = gitlab_user_url
# types of actions and their formatted form
jinja_env.globals['available_actions'] = {
    'open': 'created',
    'close': 'closed',
    'reopen': 'reopened',
    'update': 'updated',
    'merge': 'accepted',
}
# allow to raise errors
jinja_env.globals['raise'] = raise_helper


class Event(object):

    def __init__(self, data):
        self.data = data
        self.object_kind = data['object_kind']
        template_name = self.object_kind + '.j2'
        self.template = jinja_env.get_template(template_name)

    @property
    def action(self):
        try:
            self.data['object_attributes']['action']
        except KeyError:
            return ''

    def should_report_event(self, report_events):
        return report_events[self.object_kind] and self.action != "update"

    def format(self):
        return self.template.render(self.data)


def as_event(data):
    try:
        return Event(data)
    except TemplateNotFound:
        raise NotImplementedError('Unsupported event of type %s' % data['object_kind'])
