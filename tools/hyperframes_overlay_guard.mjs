/** Trusted overlay contract; authored HTML cannot redefine the approved master. */
export function validateApprovedMasterOverlay(spec) {
  const contract = spec.asset_contract?.approved_master_overlay;
  if (!contract) return;
  const validHash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
  const entry = spec.files?.find(file => file.path === 'index.html');
  const master = spec.files?.find(file => file.path === 'master.mp4');
  if (!validHash(contract.composition_sha256) || !validHash(contract.master_sha256) ||
      !validHash(contract.master_digest) || contract.master_path !== 'master.mp4' ||
      entry?.sha256 !== contract.composition_sha256 || master?.sha256 !== contract.master_sha256 ||
      Number(spec.duration_seconds) !== Number(contract.duration_seconds) ||
      spec.audio_mode !== (contract.audio === true ? 'music_only' : 'silent')) {
    throw new Error('hyperframes_overlay_contract_changed: approved master or sealed overlay composition changed');
  }
  if (contract.audio && !spec.asset_contract.required_audio?.some(asset =>
    asset.role === 'music' && asset.sha256 === contract.master_sha256)) {
    throw new Error('hyperframes_overlay_contract_changed: exact approved master audio is required');
  }
}
