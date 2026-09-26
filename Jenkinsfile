// Jenkinsfile — EventEase CI/CD Pipeline
// This pipeline automates: Code → Test → Quality → Docker → Deploy

pipeline {

    agent any

    environment {
        DOCKER_HUB_USER = credentials('docker-hub-username')
        DOCKER_HUB_PASS = credentials('docker-hub-password')
        IMAGE_NAME       = "eventease"
        IMAGE_TAG        = "${env.BUILD_NUMBER}"
        DJANGO_SETTINGS  = "event_management.settings"
    }

    stages {

        stage('📥 Checkout') {
            steps {
                echo '========== Checking out source code =========='
                git branch: 'main',
                    url: 'https://github.com/YOUR_USERNAME/event-management.git'
                sh 'echo "Branch: $(git rev-parse --abbrev-ref HEAD)"'
                sh 'echo "Commit: $(git log -1 --format=%H)"'
            }
        }

        stage('🐍 Setup Python') {
            steps {
                echo '========== Setting up Python environment =========='
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('🧪 Run Tests') {
            steps {
                echo '========== Running automated tests =========='
                sh '''
                    . venv/bin/activate
                    python manage.py test --verbosity=2 --settings=${DJANGO_SETTINGS}
                '''
            }
            post {
                always {
                    echo 'Test stage completed'
                }
                failure {
                    echo '❌ Tests FAILED — stopping pipeline'
                }
            }
        }

        stage('📊 Code Coverage') {
            steps {
                echo '========== Checking test coverage =========='
                sh '''
                    . venv/bin/activate
                    coverage run --source='.' manage.py test --settings=${DJANGO_SETTINGS}
                    coverage report --fail-under=70
                    coverage xml -o coverage.xml
                '''
            }
        }

        stage('🔍 Code Quality (SonarQube)') {
            when {
                expression { return env.SONAR_HOST_URL != null }
            }
            steps {
                echo '========== Running SonarQube analysis =========='
                withSonarQubeEnv('SonarQube') {
                    sh '''
                        sonar-scanner \
                          -Dsonar.projectKey=eventease \
                          -Dsonar.sources=. \
                          -Dsonar.language=py \
                          -Dsonar.python.coverage.reportPaths=coverage.xml
                    '''
                }
            }
        }

        stage('🐳 Docker Build') {
            steps {
                echo '========== Building Docker image =========='
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest ."
                sh "docker images | grep ${IMAGE_NAME}"
            }
        }

        stage('📤 Docker Push') {
            steps {
                echo '========== Pushing image to Docker Hub =========='
                sh """
                    echo \$DOCKER_HUB_PASS | docker login -u \$DOCKER_HUB_USER --password-stdin
                    docker tag ${IMAGE_NAME}:latest \$DOCKER_HUB_USER/${IMAGE_NAME}:${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:latest \$DOCKER_HUB_USER/${IMAGE_NAME}:latest
                    docker push \$DOCKER_HUB_USER/${IMAGE_NAME}:${IMAGE_TAG}
                    docker push \$DOCKER_HUB_USER/${IMAGE_NAME}:latest
                """
            }
        }

        stage('🚀 Deploy') {
            steps {
                echo '========== Deploying to server =========='
                sh '''
                    docker compose pull
                    docker compose up -d --no-deps --build web
                    docker compose ps
                '''
                echo '✅ Deployment successful!'
            }
        }

        stage('🏥 Health Check') {
            steps {
                echo '========== Verifying deployment =========='
                sh '''
                    sleep 10
                    curl -f http://localhost:80/ || (echo "Health check failed!" && exit 1)
                    echo "✅ Application is up and running!"
                '''
            }
        }
    }

    post {
        success {
            echo """
            ╔══════════════════════════════════╗
            ║  ✅  BUILD SUCCESS               ║
            ║  EventEase deployed successfully  ║
            ╚══════════════════════════════════╝
            """
        }
        failure {
            echo """
            ╔══════════════════════════════════╗
            ║  ❌  BUILD FAILED                ║
            ║  Check logs for details          ║
            ╚══════════════════════════════════╝
            """
        }
        always {
            sh 'docker logout || true'
            cleanWs()
        }
    }
}
