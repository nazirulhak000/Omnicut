export function shouldShowHighResolutionStillPreview({
  enabled,
  isPlaying,
  currentKey,
  preview,
}) {
  return Boolean(
    enabled === true
    && isPlaying !== true
    && preview?.src
    && preview?.key === currentKey,
  );
}
