import { IExecuteFunctions } from 'n8n-workflow';
import {
  IDataObject,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  NodeConnectionType,
} from 'n8n-workflow';
import axios, { AxiosRequestConfig } from 'axios';

export class AgentNN implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'ABrain',
    name: 'agentnn',
    group: ['transform'],
    version: 1,
    description: 'Send tasks to the ABrain dispatcher',
    defaults: {
      name: 'ABrain',
    },
    inputs: [NodeConnectionType.Main],
    outputs: [NodeConnectionType.Main],
    properties: [
      {
        displayName: 'Endpoint',
        name: 'endpoint',
        type: 'string',
        default: 'http://localhost:8000',
      },
      {
        displayName: 'Task Type',
        name: 'taskType',
        type: 'string',
        default: 'chat',
      },
      {
        displayName: 'Payload',
        name: 'payload',
        type: 'json',
        default: '{}',
      },
      {
        displayName: 'Path',
        name: 'path',
        type: 'string',
        default: '/task',
        description: 'API path appended to the endpoint',
      },
      {
        displayName: 'Method',
        name: 'method',
        type: 'options',
        options: [
          {
            name: 'POST',
            value: 'POST',
          },
          {
            name: 'GET',
            value: 'GET',
          },
        ],
        default: 'POST',
        description: 'HTTP method to use',
      },
      {
        displayName: 'Headers',
        name: 'headers',
        type: 'json',
        default: '{}',
        description: 'Optional HTTP headers',
      },
      {
        displayName: 'Timeout',
        name: 'timeout',
        type: 'number',
        default: 10000,
        description: 'Request timeout in milliseconds',
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const endpoint = this.getNodeParameter('endpoint', 0) as unknown as string;
    const taskType = this.getNodeParameter('taskType', 0) as unknown as string;
    const payload = this.getNodeParameter('payload', 0) as unknown as IDataObject;
    const path = this.getNodeParameter('path', 0, '/task') as string;
    const method = (this.getNodeParameter('method', 0, 'POST') as string).toUpperCase();
    const headers = (this.getNodeParameter('headers', 0, {}) as IDataObject) as Record<string, string>;
    const timeout = this.getNodeParameter('timeout', 0, 10000) as number;

    const options: AxiosRequestConfig = {
      method,
      url: `${endpoint}${path}`,
      data: {
        task_type: taskType,
        input: payload,
      },
      headers,
      timeout,
    };

    const { data } = await axios.request(options);

    return [[data as INodeExecutionData]];
  }
}
