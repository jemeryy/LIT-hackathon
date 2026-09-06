const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function main() {
  const script = fs.readFileSync(path.join(__dirname, 'static/index.html'), 'utf8')
    .match(/<script>([\s\S]*?)<\/script>/)[1].replace(/load\(\);\s*$/, '');
  const elements = {};
  const element = id => elements[id] ||= {value: '', textContent: '', classList: {add() {}, remove() {}}, focus() {}};
  const original = {case_id: 'mine', intake: {chat: [{who: 'bot', text: 'Previous question?'}]}, exhibits: []};
  let response = original;
  const calls = [];
  const context = vm.createContext({
    document: {getElementById: element, addEventListener() {}},
    URLSearchParams, location: {search: ''},
    fetch: async (url, options) => { calls.push([url, options]); return {json: async () => structuredClone(response)}; },
    original,
  });
  vm.runInContext(script, context);
  vm.runInContext('render = () => {}; scrollChat = () => {};', context);
  await vm.runInContext('load()', context);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], '/api/case');
  assert.equal(calls[0][1], undefined, 'refresh must read the saved case, not POST a reset');

  // The API helper installs the rolled-back case before send() handles failure.
  response = {error: 'Model failed', case: original};
  element('say').value = 'My new answer';
  await vm.runInContext('send()', context);
  assert.equal(vm.runInContext('C.intake.chat.length', context), 1);
  assert.equal(vm.runInContext('C.intake.chat[0].text', context), 'Previous question?');
  assert.equal(element('say').value, 'My new answer', 'failed message must remain available to retry');
  assert.equal(vm.runInContext('waiting', context), false);

  context.location.search = '?example=1';
  response = {...original, case_id: 'example'};
  calls.length = 0;
  await vm.runInContext('load()', context);
  assert.equal(calls.length, 1, 'refreshing an edited example must not discard the edits');

  vm.runInContext('waiting = true; step = 0;', context);
  calls.length = 0;
  await vm.runInContext('newCase()', context);
  await vm.runInContext('clearChat()', context);
  vm.runInContext('go(1)', context);
  assert.equal(calls.length, 0, 'pending chat must not race with a case reset');
  assert.equal(vm.runInContext('step', context), 0);
  context.assessmentCase = {case_id: 'example', story: '', evidence: [],
    unranked_evidence: ['context', 'placeholder', 'irrelevant', 'needs_review'].map(strength => ({
      rank: null, what: strength + ' file', strength, reason: 'Assessment reason',
      sources: [{label: 'E2', title: strength + '.png', viewer_url: '/api/viewer?asset_id=E2'}],
    })), blindspots: {theirs: []}};
  vm.runInContext('C = assessmentCase', context);
  const ranking = vm.runInContext('ranking()', context);
  for (const label of ['Context', 'Placeholder', 'Irrelevant', 'Needs review']) assert(ranking.includes(label));
  assert(!ranking.includes('undefined'));
  assert.equal((ranking.match(/Not ranked/g) || []).length, 4);
  console.log('Chat UI checks passed: refresh, edited example, failed-message retry, and navigation during pending requests.');
  console.log('Ranking UI checks passed: context, placeholder, irrelevant and needs-review rows.');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
