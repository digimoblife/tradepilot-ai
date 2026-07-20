import { post } from "./client";
import type {
  OpenPositionRequest,
  StopActionRequest,
  TargetActionRequest,
  PartialExitRequest,
  FullExitRequest,
  CancelSessionRequest,
  ActionResult,
} from "@/types/trade-action";

export function openPosition(data: OpenPositionRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/open-position", data);
}

export function confirmStop(data: StopActionRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/confirm-stop", data);
}

export function changeStop(data: StopActionRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/change-stop", data);
}

export function confirmTarget(data: TargetActionRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/confirm-target", data);
}

export function changeTarget(data: TargetActionRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/change-target", data);
}

export function partialExit(data: PartialExitRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/partial-exit", data);
}

export function fullExit(data: FullExitRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/full-exit", data);
}

export function cancelSession(data: CancelSessionRequest): Promise<ActionResult> {
  return post<ActionResult>("/api/actions/cancel", data);
}
