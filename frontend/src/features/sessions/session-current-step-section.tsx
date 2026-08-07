"use client";

import { SessionCurrentStepCard } from "@/features/sessions/session-current-step-card";
import {
  loadingCurrentStepPresentation,
  mapSessionCurrentStep,
  unavailableCurrentStepPresentation,
} from "@/features/sessions/session-current-step";
import { useSessionCurrentStep } from "@/features/sessions/use-session-current-step";
import { SessionSummaryContent } from "@/features/sessions/session-summary-content";
import { InitialAnalysisRecovery } from "@/features/sessions/initial-analysis-recovery";

import { SessionDecisionSurface } from "@/features/sessions/session-decision-surface";
import { SessionWaitingSummary } from "@/features/sessions/session-waiting-summary";
import { WaitUpdateRecovery } from "@/features/sessions/wait-update-recovery";
import { SessionOpenPositionSummary } from "@/features/sessions/session-open-position-summary";
import { PositionUpdateRecovery } from "@/features/sessions/position-update-recovery";
import { SessionTerminalSummary } from "@/features/sessions/session-terminal-summary";

export function SessionCurrentStepSection({ sessionId }: { sessionId: string }) {
  const state = useSessionCurrentStep(sessionId);
  const presentation =
    state.status === "loading"
      ? loadingCurrentStepPresentation()
      : state.status === "success"
        ? mapSessionCurrentStep(state.currentStep)
        : unavailableCurrentStepPresentation();

  return (
    <>
      <section
        aria-live={state.status === "loading" ? "polite" : undefined}
        aria-busy={state.status === "loading"}
        className="mx-auto w-full max-w-[var(--layout-application-max)] min-w-0 px-4 pb-8 sm:px-6 sm:pb-10 lg:px-8"
      >
        <SessionCurrentStepCard presentation={presentation} sessionId={sessionId} />
      </section>
      {state.status === "success" ? (
        <SessionTerminalSummary sessionId={sessionId} detail={state.detail} />
      ) : null}
      {state.status === "success" ? (
        <SessionWaitingSummary sessionId={sessionId} detail={state.detail} />
      ) : null}
      {state.status === "success" ? (
        <SessionOpenPositionSummary sessionId={sessionId} detail={state.detail} step={state.currentStep} />
      ) : null}
      {state.status === "success" ? (
        <SessionDecisionSurface sessionId={sessionId} step={state.currentStep} refetch={state.refetch} />
      ) : null}
      {state.status === "success" ? (
        <InitialAnalysisRecovery sessionId={sessionId} step={state.currentStep} refetch={state.refetch} />
      ) : null}
      {state.status === "success" ? (
        <WaitUpdateRecovery sessionId={sessionId} step={state.currentStep} refetch={state.refetch} />
      ) : null}
      {state.status === "success" ? (
        <PositionUpdateRecovery sessionId={sessionId} step={state.currentStep} refetch={state.refetch} />
      ) : null}
      {state.status === "success" ? (
        <SessionSummaryContent sessionId={sessionId} detail={state.detail} />
      ) : null}
    </>
  );
}
