// ObjC bridge — exposes Swift BrightnessModule to React Native's JS bridge
#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(BrightnessModule, NSObject)

RCT_EXTERN_METHOD(getBrightness:
                  (RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(setBrightness:
                  (float)brightness
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(dimBy:
                  (float)fraction
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(restoreBrightness:
                  (RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end
