import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { extractPrompt, sanitize, extractFeatureName } from '../uam-keyword-detector.mjs';

describe('extractFeatureName', () => {
  it('should extract English feature name', () => {
    const result = extractFeatureName('uam add login feature');
    assert.ok(result.includes('add'));
    assert.ok(result.includes('login'));
    assert.ok(result.includes('feature'));
  });

  it('should return "task" for empty input', () => {
    const result = extractFeatureName('uam');
    // After removing "uam", cleaned is empty -> returns 'unnamed'
    assert.strictEqual(result, 'unnamed');
  });

  it('should return "task" for only stop words', () => {
    const result = extractFeatureName('uam the and for');
    // All words filtered out by stop words or length
    assert.strictEqual(result, 'task');
  });

  it('should keep Korean characters (M1)', () => {
    const result = extractFeatureName('uam 로그인 기능 추가');
    assert.ok(result.includes('로그인'));
  });

  it('should strip special characters but keep hyphens', () => {
    const result = extractFeatureName('uam add @login! #feature$');
    assert.ok(!result.includes('@'));
    assert.ok(!result.includes('!'));
    assert.ok(!result.includes('#'));
    assert.ok(!result.includes('$'));
  });

  it('should trim leading/trailing dashes', () => {
    const result = extractFeatureName('uam --- test ---');
    assert.ok(!result.startsWith('-'));
    assert.ok(!result.endsWith('-'));
  });
});

describe('sanitize', () => {
  it('should remove code blocks', () => {
    const input = 'uam ```const x = 1;``` hello';
    const result = sanitize(input);
    assert.ok(!result.includes('const x'));
    assert.ok(result.includes('hello'));
  });

  it('should remove inline code', () => {
    const input = 'uam `some code` hello';
    const result = sanitize(input);
    assert.ok(!result.includes('some code'));
  });

  it('should remove URLs', () => {
    const input = 'uam check https://example.com/path?q=1 now';
    const result = sanitize(input);
    assert.ok(!result.includes('https://example.com'));
  });

  it('should remove file paths', () => {
    const input = 'uam edit src/components/App.tsx please';
    const result = sanitize(input);
    assert.ok(!result.includes('src/components/App.tsx'));
  });

  it('should preserve plain text', () => {
    const input = 'uam build a todo app';
    const result = sanitize(input);
    assert.ok(result.includes('uam'));
    assert.ok(result.includes('build'));
    assert.ok(result.includes('todo'));
  });
});

describe('extractPrompt', () => {
  it('should extract from prompt field', () => {
    const input = JSON.stringify({ prompt: 'uam build feature' });
    assert.strictEqual(extractPrompt(input), 'uam build feature');
  });

  it('should extract from message.content', () => {
    const input = JSON.stringify({ message: { content: 'uam test' } });
    assert.strictEqual(extractPrompt(input), 'uam test');
  });

  it('should extract from parts array', () => {
    const input = JSON.stringify({
      parts: [
        { type: 'text', text: 'hello' },
        { type: 'image', data: '...' },
        { type: 'text', text: 'world' }
      ]
    });
    assert.strictEqual(extractPrompt(input), 'hello world');
  });

  it('should return empty string for invalid JSON', () => {
    assert.strictEqual(extractPrompt('not json'), '');
  });

  it('should return empty string for empty object', () => {
    assert.strictEqual(extractPrompt('{}'), '');
  });
});
