import React from "react";
import "./index.css";
import { Composition } from "remotion";
import { MyComposition } from "./Composition";
import { TheOldWay } from "./TheOldWay";
import { TheNewWay } from "./TheNewWay";
import { WidgetIntro } from "./WidgetIntro";
import { PipelineDemo } from "./PipelineDemo";
import { UploadFlow } from "./UploadFlow";
import { SearchRetrieval } from "./SearchRetrieval";
import { GenerateAndSpeak } from "./GenerateAndSpeak";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MyComp"
        component={MyComposition}
        durationInFrames={60}
        fps={30}
        width={1280}
        height={720}
      />
      <Composition
        id="TheOldWay"
        component={TheOldWay}
        durationInFrames={240}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="TheNewWay"
        component={TheNewWay}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="WidgetIntro"
        component={WidgetIntro}
        durationInFrames={270}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="PipelineDemo"
        component={PipelineDemo}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="UploadFlow"
        component={UploadFlow}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="SearchRetrieval"
        component={SearchRetrieval}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="GenerateAndSpeak"
        component={GenerateAndSpeak}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
