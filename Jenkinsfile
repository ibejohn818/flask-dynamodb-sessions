#!/usr/bin/env groovy

import hudson.model.*
import hudson.EnvVars


node {

    try {

        //def img_tag = "${env.BRANCH_NAME.toLowerCase()}${env.BUILD_ID}"

        stage("Stage Repo") {
            echo "Checkout repo"
            checkout scm
        }

    } catch(Exception err) {
        currentBuild.result = "FAILURE"
    } finally {

    }
}
