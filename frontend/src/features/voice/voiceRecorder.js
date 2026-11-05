export function stopRecorderIfActive(recorder) {
  if (recorder && recorder.state !== 'inactive') recorder.stop();
}
