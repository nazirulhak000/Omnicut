import React, { useCallback, useEffect, useState } from 'react';
import { Clapperboard, Library, ShieldCheck } from 'lucide-react';

import { createGadgetMediaProject, listGadgetMediaProjects } from '../../api.js';
import { PageHeader } from '../ui';
import ProductLibrary from './ProductLibrary.jsx';
import ProductWorkspace from './ProductWorkspace.jsx';


export default function GadgetMediaStudio({ initialProjectId = '', seed = null, onSeedConsumed }) {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(initialProjectId);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await listGadgetMediaProjects();
      setProjects(response.projects || []);
    } catch (loadError) {
      setError(loadError?.response?.data?.detail || loadError?.message || 'โหลด Product Library ไม่สำเร็จ');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(loadProjects);
  }, [loadProjects]);

  const createProject = async (payload) => {
    const created = await createGadgetMediaProject(payload);
    onSeedConsumed?.();
    await loadProjects();
    return created;
  };

  if (selectedProjectId) {
    return <ProductWorkspace projectId={selectedProjectId} onBack={() => { setSelectedProjectId(''); loadProjects(); }} onProjectChanged={loadProjects} />;
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Gadget Media · Product Video Studio"
        title="หนึ่งสินค้า หนึ่งคลิป Master"
        icon={Clapperboard}
        iconGradient="from-cyan-500/25 to-violet-500/20"
        secondRow={(
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-400">
            <span className="flex items-center gap-1.5"><Library className="h-3.5 w-3.5 text-cyan-300" /> Project, Timeline และ Export แยกจากงานปักตะกร้า</span>
            <span className="flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-emerald-300" /> Native 1080p · Rights · Evidence · 45–60 วินาที</span>
          </div>
        )}
      />
      {error && <div role="alert" className="rounded-xl bg-rose-500/10 px-3 py-2 text-sm text-rose-200 ring-1 ring-rose-400/25">{error}</div>}
      <ProductLibrary projects={projects} loading={loading} onRefresh={loadProjects} onCreate={createProject} onOpen={setSelectedProjectId} seed={seed} />
    </div>
  );
}
