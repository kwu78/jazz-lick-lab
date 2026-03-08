#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { JazzLickLabStack } from "../lib/jazz-lick-lab-stack";

const app = new cdk.App();

new JazzLickLabStack(app, "JazzLickLabStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
  },
});
