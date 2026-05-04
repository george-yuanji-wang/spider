export type DriveMode = "manual" | "auto";

export interface Ctrl {
  armed:       boolean;
  mode:        DriveMode;
  input_left:  number;
  input_right: number;
  speed:       number;
  claw:       boolean;
}

export const defaultCtrl: Ctrl = {
  armed:       false,
  mode:        "manual",
  input_left:  0,
  input_right: 0,
  speed:       50,
  claw:       false,
};