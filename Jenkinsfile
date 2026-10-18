pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
    }

    environment {
        IMAGE = 'mujahiddxd/eventease'
        EC2_HOST = '98.84.188.39'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    .venv/bin/pip install -r requirements.txt
                    .venv/bin/python manage.py test --settings=event_management.settings
                '''
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t "$IMAGE:$BUILD_NUMBER" .'
            }
        }

        stage('Push image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_TOKEN'
                )]) {
                    sh '''
                        printf '%s' "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push "$IMAGE:$BUILD_NUMBER"
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to EC2') {
            steps {
                sshagent(credentials: ['ec2-ssh']) {
                    sh '''
                        ssh -o StrictHostKeyChecking=accept-new ubuntu@"$EC2_HOST" \
                          "cd ~/Event_Ease && \
                           sudo env IMAGE_TAG=$BUILD_NUMBER docker compose pull web && \
                           sudo env IMAGE_TAG=$BUILD_NUMBER docker compose up -d --no-deps web"
                    '''
                }
            }
        }

        stage('Health check') {
            steps {
                sh '''
                    curl --fail --retry 8 --retry-delay 3 --retry-connrefused \
                        "http://$EC2_HOST/" > /dev/null
                '''
            }
        }
    }
}
