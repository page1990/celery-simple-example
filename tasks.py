#-*- encoding: utf-8 -*-
from __future__ import absolute_import

from celery import Celery

import requests

app = Celery('tasks', broker='amqp://localhost', backend='amqp://localhost')

@app.task
def update():
    data = {
        'id': 2,
        'hostname': 'www.test222sss.com',
        'belongs_to_PlatForm': '招行',
        'host_network_area': 'SIT-WEB-WEB',
        'host_status': '0',
        'host_cpu': '2',
        'host_mem': '16G',
        'host_disk': '50G',
        'belongs_to_ostype': 'centos',
        'host_remarks': 'test2'
    }
    url = 'http://127.0.0.1/api/host/'
    headers = {
        'Authorization': 'Token your_token'
    }
    r = requests.put(url, data=data, headers=headers)
    return r.status_code
