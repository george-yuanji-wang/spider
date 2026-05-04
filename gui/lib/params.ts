export interface BallTrackParams {
  hue_low:     number;
  hue_high:    number;
  sat_low:     number;
  sat_high:    number;
  val_low:     number;
  val_high:    number;
  min_radius:  number;
  blur_kernel: number;
  dilate_iter: number;
}

export interface Params {
  ball: BallTrackParams;
}

export const defaultParams: Params = {
  ball: {
    hue_low:     90,
    hue_high:    106,
    sat_low:     100,
    sat_high:    220,
    val_low:     100,
    val_high:    255,
    min_radius:  8,
    blur_kernel: 2,
    dilate_iter: 1,
  },
};