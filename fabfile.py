from fabric.api import task, env
from fabric.context_managers import cd, prefix, settings
from fabric.operations import sudo

env.hosts = env.hosts or ['artunium.futurice.com']
code_dir = '/home/sforce2flowdock/sforce2flowdock'
code_dir_user = 'sforce2flowdock'
venv_dir = '/home/sforce2flowdock/venv'

@task
def deploy():
    with settings(cd(code_dir), sudo_user=code_dir_user):
        sudo('git pull')
        with prefix('source ' + venv_dir + '/bin/activate'):
            sudo('pip install -r req.txt')
