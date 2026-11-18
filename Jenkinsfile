pipeline {
    agent any

    environment {
        IMAGE_VERSION  = "v2.1.${BUILD_NUMBER}"
        BACKEND_IMAGE  = "ghcr.io/vedanth-js/ai-ats-api"
        FRONTEND_IMAGE = "ghcr.io/vedanth-js/ai-ats-frontend"
        APP_ENV        = "test"
    }

    stages {
        stage('1. Checkout Source Code') {
            steps {
                checkout scm
                echo "Checked out commit ${env.GIT_COMMIT} on branch ${env.BRANCH_NAME}"
            }
        }

        stage('2. Backend Automated Tests (Pytest)') {
            steps {
                script {
                    if (isUnix()) {
                        sh '''
                            python3 -m venv .venv
                            .venv/bin/pip install --upgrade pip
                            .venv/bin/pip install -r backend/requirements.txt pytest pytest-asyncio
                            .venv/bin/pytest backend/tests/test_ats_scoring_engine.py backend/tests/test_api.py -v --junitxml=backend/test-results.xml
                        '''
                    } else {
                        bat '''
                            python -m venv .venv
                            .venv\\Scripts\\pip install -r backend\\requirements.txt pytest pytest-asyncio
                            .venv\\Scripts\\python -m pytest backend\\tests\\test_ats_scoring_engine.py backend\\tests\\test_api.py -v --junitxml=backend\\test-results.xml
                        '''
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'backend/test-results.xml'
                }
            }
        }

        stage('3. Frontend Production Build (Vite)') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'npm install && npm run build'
                    } else {
                        bat 'npm install && npm run build'
                    }
                }
            }
        }

        stage('4. Docker Build & Versioned Tagging') {
            steps {
                script {
                    if (isUnix()) {
                        sh """
                            docker build -t ${BACKEND_IMAGE}:${IMAGE_VERSION} -t ${BACKEND_IMAGE}:latest ./backend
                            docker build -f frontend/Dockerfile.prod -t ${FRONTEND_IMAGE}:${IMAGE_VERSION} -t ${FRONTEND_IMAGE}:latest ./frontend
                        """
                    } else {
                        bat """
                            docker build -t %BACKEND_IMAGE%:%IMAGE_VERSION% -t %BACKEND_IMAGE%:latest ./backend
                            docker build -f frontend/Dockerfile.prod -t %FRONTEND_IMAGE%:%IMAGE_VERSION% -t %FRONTEND_IMAGE%:latest ./frontend
                        """
                    }
                }
            }
        }

        stage('5. Deploy Prebuilt to Vercel Production') {
            when {
                branch 'main'
            }
            steps {
                withCredentials([
                    string(credentialsId: 'VERCEL_TOKEN', variable: 'VERCEL_TOKEN'),
                    string(credentialsId: 'VERCEL_ORG_ID', variable: 'VERCEL_ORG_ID'),
                    string(credentialsId: 'VERCEL_PROJECT_ID', variable: 'VERCEL_PROJECT_ID')
                ]) {
                    script {
                        if (isUnix()) {
                            sh '''
                                npm install -g vercel@65.17.0
                                vercel pull --yes --environment=production --token=$VERCEL_TOKEN
                                vercel build --prod --token=$VERCEL_TOKEN
                                vercel deploy --prebuilt --prod --yes --token=$VERCEL_TOKEN
                            '''
                        } else {
                            bat '''
                                npm install -g vercel@65.17.0
                                vercel pull --yes --environment=production --token=%VERCEL_TOKEN%
                                vercel build --prod --token=%VERCEL_TOKEN%
                                vercel deploy --prebuilt --prod --yes --token=%VERCEL_TOKEN%
                            '''
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            echo "CI/CD Pipeline PASSED! Version ${IMAGE_VERSION} tested, containerized, and deployed to Vercel."
        }
        failure {
            echo "CI/CD Pipeline FAILED! Check test or build stage logs."
        }
        always {
            cleanWs()
        }
    }
}
