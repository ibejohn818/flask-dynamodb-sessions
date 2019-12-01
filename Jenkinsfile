#!/usr/bin/env groovy

import hudson.model.*
import hudson.EnvVars


node {

    try {

        def img_tag = "flaskddbtest"

        // load shared jenkins code
        @Library('shared-pipelines')_

        stage("Stage Repo") {
            echo "Checkout repo"
            checkout scm
        }

        stage("Build test image") {
            sh "docker build -f Dockerfile.jenkins -t ${img_tag} ."
        }

        stage("Run Tests") {
            sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} -v /etc/passwd:/etc/passwd:ro -ujhardy ${img_tag} python3 setup.py covxml"
            sh "chmod -R 777 ${env.WORKSPACE}"
            currentBuild.result = "SUCCESS"
        }

        stage("Send Code Coverage") {
            if (currentBuild.result == "SUCCESS") {
               codecovio("FlaskDynamoSessionCodeCov")
            } else {
                echo "Skipping coverage report..."
            }
        }

        if (env.TAG_NAME && currentBuild.result == "SUCCESS") {
            stage("Publish To PyPi") {
                pypi(env.WORKSPACE, "flask-dynamodb-session", img_tag)
            }
        }

    } catch(Exception err) {
        currentBuild.result = "FAILURE"
    } finally {

    }
}
