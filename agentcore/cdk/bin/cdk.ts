#!/usr/bin/env node
import { App, Tags } from 'aws-cdk-lib';
import { readAgentCoreProject, resolveTargetStacks, transformAgentCoreJson } from '@aws/agentcore-cdk';
import { AgentCoreStack } from '../lib/cdk-stack';

try {
  // The AgentCore CLI runs this app from agentcore/cdk/; readAgentCoreProject walks up to agentcore/.
  const project = readAgentCoreProject();
  const app = new App();
  for (const stack of resolveTargetStacks({
    projectName: project.projectName,
    targets: project.targets,
    deployedState: project.deployedState,
  })) {
    new AgentCoreStack(app, stack.stackName, {
      env: stack.env,
      tags: stack.tags,
      description: stack.description,
      application: transformAgentCoreJson(project.agentCoreJson, {
        projectRoot: project.projectRoot,
        credentials: stack.credentials,
        target: stack.target,
      }),
    });
  }
  // Every resource the CLI creates carries the project tags (same pair as infra/app.py).
  Tags.of(app).add('Project', 'agentcore-surveillance-investigator');
  Tags.of(app).add('auto-delete', 'no');
  app.synth();
} catch (error) {
  console.error('AgentCore CDK synthesis failed:', error instanceof Error ? error.message : error);
  process.exit(1);
}
