class VirtualHarvesterConfig:
    def _check_and_complete(self, verbose: bool = True):
        # factor-in timing-constraints
        _window_samples = self.data["window_size"] * (1 + self.data["wait_cycles"])

        time_min_ms = (1 + self.data["wait_cycles"]) * 1_000 / self.samplerate_sps
        if self.for_emulation:
            window_ms = _window_samples * 1_000 / self.samplerate_sps
            time_min_ms = max(time_min_ms, window_ms)

        ratio_old = self.data["duration_ms"] / self.data["interval_ms"]
        self._check_num("interval_ms", time_min_ms, 1_000_000, verbose=verbose)
        self._check_num(
            "duration_ms",
            time_min_ms,
            self.data["interval_ms"],
            verbose=verbose,
        )
        ratio_new = self.data["duration_ms"] / self.data["interval_ms"]
        if (ratio_new / ratio_old - 1) > 0.1:
            logger.debug(
                "Ratio between interval & duration has changed "
                "more than 10%% due to constraints, from %.4f to %.4f",
                ratio_old,
                ratio_new,
            )

        if "dtype" not in self.data and "dtype" in self._config_base:
            self.data["dtype"] = self._config_base["dtype"]

        # for proper emulation and harvesting (this var decides how h5-file is treated)
        if "window_samples" not in self.data:
            self.data["window_samples"] = _window_samples
        if (
            self.for_emulation
            and (self.data["window_samples"] > 0)
            and (_window_samples > self.data["window_samples"])
        ):
            # TODO: verify that this works ->
            #  if window_samples are zero (set from datalog-reader) they should
            #  stay zero to disable hrv-routine during emulation
            self.data["window_samples"] = _window_samples
        if verbose:
            logger.debug("window_samples = %d", self.data["window_samples"])
