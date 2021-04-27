import requests
import json
import copy
from elastalert.alerts import Alerter, BasicMatchString, DateTimeEncoder
from elastalert.util import lookup_es_key, elastalert_logger, EAException
from requests.exceptions import RequestException

class myMsTeamsAlerter(Alerter):
    
    required_options = set(['ms_teams_webhook_url', 'ms_teams_alert_summary', 'ms_teams_index_pattern_url'])

    link_pattern = {
        '@type': 'OpenUri',
        'name': '',
        'targets': []
    }

    target_pattern = {
        'os': 'default',
        'uri': ''
    }

    def __init__(self, rule):
        super(myMsTeamsAlerter, self).__init__(rule)
        self.ms_teams_webhook_url = self.rule['ms_teams_webhook_url']
        if isinstance(self.ms_teams_webhook_url, str):
            self.ms_teams_webhook_url = [self.ms_teams_webhook_url]
        self.ms_teams_proxy = self.rule.get('ms_teams_proxy', None)
        self.ms_teams_alert_summary = self.rule.get('ms_teams_alert_summary', 'ElastAlert Message')
        self.ms_teams_alert_title = self.rule.get('ms_teams_alert_title', '')
        self.ms_teams_alert_fields = self.rule.get('ms_teams_alert_fields', '')
        self.ms_teams_theme_color = self.rule.get('ms_teams_theme_color', 'FF0000')
        self.ms_teams_index_pattern_url = self.rule.get('ms_teams_index_pattern_url', '')
        self.ms_teams_alert_links = self.rule.get('ms_teams_alert_links', '')

    def populate_fields(self, matches):
        alert_fields = []
        for arg in self.ms_teams_alert_fields:
            arg = copy.copy(arg)
            arg['value'] = lookup_es_key(matches[0], arg['value'])
            alert_fields.append(arg)
        return alert_fields

        def populate_title(self, matches):
            return lookup_es_key(matches[0], self.ms_teams_alert_title)

    def populate_links(self, matches):
        alert_links = []
        if self.ms_teams_index_pattern_url != '':
            document_id = lookup_es_key(matches[0], 'UniqueId')
            my_url = '%s%s' % (self.ms_teams_index_pattern_url,document_id)
            name = "Discover in Kibana"

            current_link_pattern = copy.copy(self.link_pattern)
            current_target_pattern = copy.copy(self.target_pattern)

            current_link_pattern['name'] = name

            target_wrapper = []
            target_wrapper.append(current_target_pattern)
            current_link_pattern['targets'] = target_wrapper
            current_link_pattern['targets'][0]['uri'] = my_url

            alert_links.append(current_link_pattern)
        if self.ms_teams_alert_links != '':
            for arg in self.ms_teams_alert_links:
                link_url = lookup_es_key(matches[0], arg['value'])
                name = arg['name']

                current_link_pattern = copy.copy(self.link_pattern)
                current_target_pattern = copy.copy(self.target_pattern)

                if link_url != '' and link_url is not None:
                    current_link_pattern['name'] = name

                    target_wrapper = []
                    target_wrapper.append(current_target_pattern)
                    current_link_pattern['targets'] = target_wrapper
                    current_link_pattern['targets'][0]['uri'] = link_url

                    alert_links.append(current_link_pattern) 
        return alert_links

    def alert(self, matches):
        headers = {'content-type': 'application/json'}
        proxies = {'https': self.ms_teams_proxy} if self.ms_teams_proxy else None

        payload = {
            '@type': 'MessageCard',
            '@context': 'http://schema.org/extensions',
            'themeColor': self.ms_teams_theme_color,
            'summary': self.ms_teams_alert_summary,
            'sections': [
                {
                    'activityTitle': self.create_title(matches),
                    'facts': [],
                    'markdown': True
                }
            ],
            'potentialAction': []
        }

        if self.ms_teams_alert_title != '':
            payload['sections'][0]['activityTitle'] = self.populate_title(matches)

        if self.ms_teams_alert_fields != '':
            payload['sections'][0]['facts'] = self.populate_fields(matches)

        if self.ms_teams_alert_links != '' or self.ms_teams_index_pattern_url != '':
            payload['potentialAction'] = self.populate_links(matches)

        with open('/opt/elastalert/elastalert_modules/alerter_test_output.log', 'a') as outfile:
            json.dump(payload, outfile)

        for url in self.ms_teams_webhook_url:
            try:
                response = requests.post(url, data=json.dumps(payload, cls=DateTimeEncoder), headers=headers, proxies=proxies)
                response.raise_for_status()
            except RequestException as e:
                raise EAException("Error posting to ms teams: %s" % e)
        elastalert_logger.info("Alert sent to MS Teams")

    def get_info(self):
        return {'type': 'ms_teams',
                'ms_teams_webhook_url': self.ms_teams_webhook_url}