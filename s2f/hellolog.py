import logging

def getLogger():
    return logging.getLogger(__name__)

def sayHello():
    getLogger().info('Hello')
