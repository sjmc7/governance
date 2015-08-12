#!/usr/bin/env python

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys
import time

import requests
import yaml

import base

s = requests.session()

six_months = int(time.time() - 30*6*24*60*60)  # 6 months ago


def get_core_reviews_by_company(group):
    # reviews by individual
    reviews = s.get('http://stackalytics.com/api/'
                    '1.0/stats/engineers?metric=marks&release=all'
                    '&start_date=%s&project_type=all'
                    '&module=%s' % (six_months, group)).json()
    companies = {}
    for eng in reviews['stats']:
        if eng['core'] != 'master':
            continue
        company = s.get('http://stackalytics.com/api/1.0/'
                        'stats/companies?metric=marks&'
                        'module=%s&user_id=%s&project_type=all'
                        '&release=all&start_date=%s'
                        % (group, eng['id'],
                           six_months)).json()['stats'][0]['id']
        companies.setdefault(company, {'reviewers': 0, 'reviews': 0})
        companies[company]['reviews'] += eng['metric']
        companies[company]['reviewers'] += 1
    return companies


def get_diversity_stats(project):
    team_stats = {}
    # commits by company
    group = "%s-group" % project.lower()
    commits = s.get('http://stackalytics.com/api/'
                    '1.0/stats/companies?metric=commits&release=all'
                    '&project_type=all&module=%s&start_date=%s'
                    % (group, six_months)).json()
    # reviews by company
    reviews = s.get('http://stackalytics.com/api/'
                    '1.0/stats/companies?metric=marks&release=all'
                    '&project_type=all&module=%s&start_date=%s'
                    % (group, six_months)).json()
    core_reviews_by_company = get_core_reviews_by_company(group)
    commits_total = sum([company['metric'] for company in commits['stats']])
    top2 = [
        commits['stats'][0]['metric'] if len(commits['stats']) > 0 else 0,
        commits['stats'][1]['metric'] if len(commits['stats']) > 1 else 0,
    ]
    team_stats['commits_top'] = (
        (float(top2[0]) / commits_total * 100) if commits_total else 0)
    team_stats['commits_top2'] = (
        (float(sum(top2)) / commits_total * 100) if commits_total else 0)

    reviews_total = sum([company['metric'] for company in reviews['stats']])
    top2 = [
        reviews['stats'][0]['metric'] if len(reviews['stats']) > 0 else 0,
        reviews['stats'][1]['metric'] if len(reviews['stats']) > 1 else 0,
    ]
    team_stats['reviews_top'] = (
        (float(top2[0]) / reviews_total * 100) if reviews_total else 0)
    team_stats['reviews_top2'] = (
        (float(sum(top2)) / reviews_total * 100) if reviews_total else 0)
    core_review_values = [company['reviews'] for company in
                          core_reviews_by_company.itervalues()]
    if len(core_review_values) == 1:
        core_review_values = [core_review_values[0], 0]
    core_review_values.sort(reverse=True)
    core_reviews_total = sum(core_review_values)
    team_stats['core_reviews_top'] = (
        (float(core_review_values[0]) / core_reviews_total * 100)
        if core_reviews_total else 0)
    team_stats['core_reviews_top2'] = (
        ((float(core_review_values[0]) + float(core_review_values[1])) /
         core_reviews_total * 100) if core_reviews_total else 0)
    core_reviewers_values = [company['reviewers'] for company in
                             core_reviews_by_company.itervalues()]
    if len(core_reviewers_values) == 1:
        core_reviewers_values = [core_reviewers_values[0], 0]
    core_reviewers_values.sort(reverse=True)
    core_reviewers_total = sum(core_reviewers_values)
    team_stats['core_reviewers_top'] = (
        (float(core_reviewers_values[0]) / core_reviewers_total * 100)
        if core_reviewers_total else 0)
    team_stats['core_reviewers_top2'] = (
        ((float(core_reviewers_values[0]) + float(core_reviewers_values[1])) /
        core_reviewers_total * 100) if core_reviewers_total else 0)

    return team_stats


def get_diversity(team):
    team_stats = get_diversity_stats(team)
    is_diverse = all((
        (team_stats['commits_top'] <= 50),
        (team_stats['reviews_top'] <= 50),
        (team_stats['core_reviews_top'] <= 50),
        (team_stats['core_reviewers_top'] <= 50),
        (team_stats['commits_top2'] <= 80),
        (team_stats['reviews_top2'] <= 80),
        (team_stats['core_reviews_top2'] <= 80),
        (team_stats['core_reviewers_top2'] <= 80),
    ))
    return is_diverse


def print_diversity(team):
    team_stats = get_diversity_stats(team)
    print '%-18s (%.2f%% | %.2f%% | %.2f%% | %.2f%%)' % (
        team, team_stats['commits_top'], team_stats['reviews_top'],
        team_stats['core_reviews_top'], team_stats['core_reviewers_top'])
    print '%-18s (%.2f%% | %.2f%% | %.2f%% | %.2f%%)' % (
        '', team_stats['commits_top2'], team_stats['reviews_top2'],
        team_stats['core_reviews_top2'], team_stats['core_reviewers_top2'])


class ValidateDiversity(base.ValidatorBase):

    @staticmethod
    def validate(team):
        """Return True of team should have 'team:diverse-affiliation'"""
        return get_diversity(team)

    @staticmethod
    def get_tag_name():
        return "team:diverse-affiliation"


def main():
    filename = os.path.abspath('reference/projects.yaml')
    with open(filename, 'r') as f:
        projects = [k for k in yaml.load(f.read())]
        projects.sort()
    print '<Team> (top commit % | top review % | top core review % | ' \
        'top core reviewer %)'
    print '       (top 2 commit % | top 2 review % | top 2 core review % | ' \
        'top 2 core reviewer %)'
    for project in projects:
        print_diversity(project)


if __name__ == '__main__':
    sys.exit(main())
