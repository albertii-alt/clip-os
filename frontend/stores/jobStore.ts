import { create } from 'zustand';
import { Job, Clip } from '@/lib/api';

interface JobStore {
  activeJobId: string | null;
  jobs: Job[];
  clips: Record<string, Clip[]>;
  setActiveJobId: (id: string | null) => void;
  setJobs: (jobs: Job[]) => void;
  setClips: (jobId: string, clips: Clip[]) => void;
  updateJob: (job: Job) => void;
}

export const useJobStore = create<JobStore>((set) => ({
  activeJobId: null,
  jobs: [],
  clips: {},
  setActiveJobId: (id) => set({ activeJobId: id }),
  setJobs: (jobs) => set({ jobs }),
  setClips: (jobId, clips) =>
    set((state) => ({ clips: { ...state.clips, [jobId]: clips } })),
  updateJob: (job) =>
    set((state) => ({
      jobs: state.jobs.map((j) => (j.id === job.id ? job : j)),
    })),
}));
