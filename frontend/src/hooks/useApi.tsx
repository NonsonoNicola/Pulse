import { useState, useCallback } from 'react';
import {
  getStatus as apiGetStatus,
  getTrends as apiGetTrends,
  getBooklet as apiGetBooklet,
  exportBooklet as apiExportBooklet,
  getCrewSummary as apiGetCrewSummary,
  getCrewMembers as apiGetCrewMembers,
  submitCheckin as apiSubmitCheckin,
  skipCheckin as apiSkipCheckin,
  getSymptoms as apiGetSymptoms,
  chat as apiChat,
  chatStream as apiChatStream,
  startEmergency as apiStartEmergency,
  getCase as apiGetCase,
  getCases as apiGetCases,
  addCaseNote as apiAddCaseNote,
  getSBARPackets as apiGetSBARPackets,
  generateSBAR as apiGenerateSBAR,
  getSyncQueue as apiGetSyncQueue,
  flushSync as apiFlushSync,
  getLinkStatus as apiGetLinkStatus,
  setLinkConfig as apiSetLinkConfig,
  getNotifications as apiGetNotifications,
  markNotificationRead as apiMarkNotificationRead,
  generateNotifications as apiGenerateNotifications,
  runScenario as apiRunScenario,
  getDemoState as apiGetDemoState,
  resetDemo as apiResetDemo,
  getEvents as apiGetEvents,
  health as apiHealth,
} from '../api/client';
import type { Assessment } from '../types';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async <T,>(
    fn: () => Promise<T>,
    options?: { onError?: (err: Error) => void }
  ): Promise<T | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await fn();
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      options?.onError?.(err instanceof Error ? err : new Error(message));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const getStatus = useCallback(
    (astronautId: string, locale = 'en') => execute(() => apiGetStatus(astronautId, locale)),
    [execute]
  );

  const getTrends = useCallback(
    (astronautId: string, days = 30, locale = 'en') =>
      execute(() => apiGetTrends(astronautId, days, locale)),
    [execute]
  );

  const getBooklet = useCallback(
    (astronautId: string) => execute(() => apiGetBooklet(astronautId)),
    [execute]
  );

  const exportBooklet = useCallback(
    (astronautId: string) => execute(() => apiExportBooklet(astronautId)),
    [execute]
  );

  const getCrewSummary = useCallback(
    (locale = 'en') => execute(() => apiGetCrewSummary(locale)),
    [execute]
  );

  const getCrewMembers = useCallback(
    () => execute(() => apiGetCrewMembers()),
    [execute]
  );

  const submitCheckin = useCallback(
    (payload: unknown) => execute(() => apiSubmitCheckin(payload)),
    [execute]
  );

  const skipCheckin = useCallback(
    (payload: unknown) => execute(() => apiSkipCheckin(payload)),
    [execute]
  );

  const getSymptoms = useCallback(
    (locale = 'en') => execute(() => apiGetSymptoms(locale)),
    [execute]
  );

  const chat = useCallback(
    (payload: Parameters<typeof apiChat>[0]) => execute(() => apiChat(payload)),
    [execute]
  );

  const chatStream = useCallback(
    (
      payload: Parameters<typeof apiChatStream>[0],
      onChunk: (chunk: string) => void,
      onDone: (assessment: Assessment) => void
    ) => {
      setLoading(true);
      setError(null);
      return apiChatStream(payload, onChunk, (assessment) => {
        setLoading(false);
        onDone(assessment);
      }).catch((err: Error) => {
        setLoading(false);
        setError(err.message);
      });
    },
    []
  );

  const startEmergency = useCallback(
    (payload: Parameters<typeof apiStartEmergency>[0]) => execute(() => apiStartEmergency(payload)),
    [execute]
  );

  const getCase = useCallback(
    (caseId: string) => execute(() => apiGetCase(caseId)),
    [execute]
  );

  const getCases = useCallback(
    () => execute(() => apiGetCases()),
    [execute]
  );

  const addCaseNote = useCallback(
    (caseId: string, payload: Parameters<typeof apiAddCaseNote>[1]) =>
      execute(() => apiAddCaseNote(caseId, payload)),
    [execute]
  );

  const getSBARPackets = useCallback(
    (caseId: string) => execute(() => apiGetSBARPackets(caseId)),
    [execute]
  );

  const generateSBAR = useCallback(
    (caseId: string) => execute(() => apiGenerateSBAR(caseId)),
    [execute]
  );

  const getSyncQueue = useCallback(
    (status?: string, limit = 100) => execute(() => apiGetSyncQueue(status, limit)),
    [execute]
  );

  const flushSync = useCallback(
    () => execute(() => apiFlushSync()),
    [execute]
  );

  const getLinkStatus = useCallback(
    () => execute(() => apiGetLinkStatus()),
    [execute]
  );

  const setLinkConfig = useCallback(
    (rttSeconds: number, mode?: string) => execute(() => apiSetLinkConfig(rttSeconds, mode)),
    [execute]
  );

  const getNotifications = useCallback(
    (unreadOnly = false, limit = 50) =>
      execute(() => apiGetNotifications(unreadOnly, limit)),
    [execute]
  );

  const markNotificationRead = useCallback(
    (id: string) => execute(() => apiMarkNotificationRead(id)),
    [execute]
  );

  const generateNotifications = useCallback(
    () => execute(() => apiGenerateNotifications()),
    [execute]
  );

  const runScenario = useCallback(
    (scenario: string, action: string) => execute(() => apiRunScenario(scenario, action)),
    [execute]
  );

  const getDemoState = useCallback(
    () => execute(() => apiGetDemoState()),
    [execute]
  );

  const resetDemo = useCallback(
    () => execute(() => apiResetDemo()),
    [execute]
  );

  const getEvents = useCallback(
    (astronautId: string, limit = 200) => execute(() => apiGetEvents(astronautId, limit)),
    [execute]
  );

  const health = useCallback(
    () => execute(() => apiHealth()),
    [execute]
  );

  return {
    loading,
    error,
    getStatus,
    getTrends,
    getBooklet,
    exportBooklet,
    getCrewSummary,
    getCrewMembers,
    submitCheckin,
    skipCheckin,
    getSymptoms,
    chat,
    chatStream,
    startEmergency,
    getCase,
    getCases,
    addCaseNote,
    getSBARPackets,
    generateSBAR,
    getSyncQueue,
    flushSync,
    getLinkStatus,
    setLinkConfig,
    getNotifications,
    markNotificationRead,
    generateNotifications,
    runScenario,
    getDemoState,
    resetDemo,
    getEvents,
    health,
  };
}
