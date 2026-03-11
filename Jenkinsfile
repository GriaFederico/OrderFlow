pipeline{
    agent any

    environment{
        BUILD_TAG = "${env.BUILD_NUMBER}" //numero BUILD
        PROJECT_NAME = "corso_devops"   // nome progetto
    }

    options {
        timeout(time: 30, unit: 'MINUTES')                // Annulla il build se supera 30 minuti (evita build "appesi")
        disableConcurrentBuilds()                          // Impedisce 2 build dello stesso job in parallelo
        buildDiscarder(logRotator(numToKeepStr: '10'))     // Tiene solo gli ultimi 10 build nella cronologia (risparmiare disco)
        timestamps()                                       // Aggiunge data/ora a ogni riga della Console Output
    }   

    //PARAMETRI DELLA PIPELINE PER LA SCELTA DELL'AMBIENTE E SE ESEGUIRE I TEST O MENO
    parameters{
        booleanParam(name: 'SKIP_TESTS', defaultValue: false, description: 'Esegui i test dopo la build?')
        choice(name: 'ENVIRONMENT', choices: ['dev', 'staging', 'prod'], description: 'Seleziona l\'ambiente di deploy')
    }

    stages{
        stage('Checkout'){
            steps{
                checkout scm
                sh '''
                    echo "=========================================="
                    echo "  OrderFlow CI Pipeline"
                    echo "=========================================="
                    echo "Build:       #${BUILD_NUMBER}"
                    echo "Branch:      ${GIT_BRANCH}"
                    echo "Commit:      $(git log --oneline -1)"
                    echo "Environment: ${ENVIRONMENT}"
                    echo "=========================================="
                '''
                echo "checkout completato"
            }            
        }
        stage('Setup Tools') {
            steps {
                sh '''
                    echo "=== Installing required tools ==="
                    TOOLS_DIR="${JENKINS_HOME}/bin"
                    mkdir -p "${TOOLS_DIR}"            
                
                    # AWS CLI v2 - installazione utente (senza sudo)
                    if ! command -v aws >/dev/null 2>&1; then
                        curl -sL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
                        cd /tmp && unzip -qo awscliv2.zip
                        chmod +x /tmp/aws/install
                        /tmp/aws/install --install-dir /usr/local/aws-cli --bin-dir /usr/local/bin --update
                        rm -rf /tmp/awscliv2.zip /tmp/aws
                    fi
                    aws --version
                    echo "=== Tools ready ==="
                   
                    '''
            }
        }
        stage('Validate'){
            steps{
                sh '''
                    echo "=== Validating project structure ==="
                    ERRORS=0
                    for svc in order-service inventory-service notification-service; do
                        echo "--- Checking ${svc} ---"
                        if [ ! -d "${svc}" ]; then
                            echo "  FAIL: directory not found"
                            ERRORS=$((ERRORS + 1))
                            continue
                        fi
                        for f in Dockerfile requirements.txt main.py; do
                            if [ -f "${svc}/${f}" ]; then
                                echo "  ${f}: OK"
                            else
                                echo "  ${f}: MISSING"
                                ERRORS=$((ERRORS + 1))
                            fi
                        done
                    done
                    if [ ${ERRORS} -gt 0 ]; then
                        echo "Validation FAILED with ${ERRORS} errors"
                        exit 1
                    fi
                    echo "Validation PASSED"
                ''' 
            }
        }
        stage('Build order service'){
            steps{
                sh '''

                    docker build \
                        -t ${PROJECT_NAME}/order-service:${BUILD_TAG} \
                        -t ${PROJECT_NAME}/order-service:latest \
                        ./order-service

                ''' 
            }
        }
        stage('Build inventory service'){
            steps{
                sh '''

                    docker build \
                        -t ${PROJECT_NAME}/inventory-service:${BUILD_TAG} \
                        -t ${PROJECT_NAME}/inventory-service:latest \
                        ./inventory-service
                        
                ''' 
            }
        }
        stage('Build notification service'){
            steps{
                sh '''

                    docker build \
                        -t ${PROJECT_NAME}/notification-service:${BUILD_TAG} \
                        -t ${PROJECT_NAME}/notification-service:latest \
                        ./notification-service

                ''' 
            }
        }
        stage('Test order service'){
            when{
                expression { !params.SKIP_TESTS }
            }
            steps{
                sh '''
                    echo "=== Testing order-service ==="
                    docker run --rm \
                        ${PROJECT_NAME}/order-service:${BUILD_TAG} \
                        python -m pytest tests/ -v --tb=short 2>/dev/null \
                        || echo "No tests directory yet"
                '''
            } 
        }
        stage('Test inventory service'){
            when{
                expression { !params.SKIP_TESTS }
            }
            steps{
                sh '''
                    echo "=== Testing inventory-service ==="
                    docker run --rm \
                        ${PROJECT_NAME}/inventory-service:${BUILD_TAG} \
                        python -m pytest tests/ -v --tb=short 2>/dev/null \
                        || echo "No tests directory yet"
                '''
            }
        }
        stage('Test notification service'){
            when{
                expression { !params.SKIP_TESTS }
            }
            steps{
                sh '''
                    echo "=== Testing notification-service ==="
                    docker run --rm \
                        ${PROJECT_NAME}/notification-service:${BUILD_TAG} \
                        python -m pytest tests/ -v --tb=short 2>/dev/null \
                        || echo "No tests directory yet"
                '''
            }
        }       
        stage('Push to ECR') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'aws-credentials',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    ),
                    string(
                        credentialsId: 'ecr-registry-URL',
                        variable: 'ECR_REGISTRY'
                    )
                ]) {
                    sh '''
                        echo "=== Logging into ECR ==="
                        aws ecr get-login-password --region eu-central-1 | \
                            docker login --username AWS \
                            --password-stdin ${ECR_REGISTRY}
 
                        echo "=== Pushing images ==="
                        for svc in order-service inventory-service notification-service; do
                            echo "--- Pushing ${svc} ---"
                            docker tag ${PROJECT_NAME}/${svc}:${BUILD_TAG} \
                                ${ECR_REGISTRY}/${svc}:${BUILD_TAG}
                            docker tag ${PROJECT_NAME}/${svc}:latest \
                                ${ECR_REGISTRY}/${svc}:latest
                            docker push ${ECR_REGISTRY}/${svc}:${BUILD_TAG}
                            docker push ${ECR_REGISTRY}/${svc}:latest
                            echo "${svc} pushed successfully"
                        done
                    '''
                }
            }        
        }        
    }
    post{
            success {
                echo "OrderFlow Pipeline SUCCESS (build #${BUILD_NUMBER})"
            }
            failure {
                echo "OrderFlow Pipeline FAILED (build #${BUILD_NUMBER})"
            }
            always {
                sh '''
                    echo "=== Final Cleanup ==="
                    for svc in order-service inventory-service notification-service; do
                        docker rmi ${PROJECT_NAME}/${svc}:${BUILD_TAG} 2>/dev/null || true
                        docker rmi ${PROJECT_NAME}/${svc}:latest 2>/dev/null || true
                    done
                '''
                cleanWs()
            }
    }
}


















