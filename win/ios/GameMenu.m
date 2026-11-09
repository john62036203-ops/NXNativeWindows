// The in-game menu without Swift (upstream: dm/ios/Sources/GameMenu.swift): dm_game_menu() for the gamepad's menu button (DmGamepad.m), a retained UIMenu rebuilt each time it opens.
// This build has no settings model to draw from (win/ios/Launcher.m keeps the settings screen's rows to itself), so the menu holds the controller layout only, as the Swift menu
// does in an app without a settings screen. The frame-rate counter and the other live settings stay on the start screen (Launcher.m).
#import <UIKit/UIKit.h>
#include "DmGameMenu.h"

static UIMenu *game_menu_items(void) {
    NSArray<NSString *> *names = @[@"2D", @"3D", @"Tap", @"Native"];
    NSMutableArray<UIMenuElement *> *layouts = [NSMutableArray array];
    for (int l = 0; l < 4; l++) {
        if (!dm_pad_layout_offered(l)) continue;
        int pick = l;
        UIAction *a = [UIAction actionWithTitle:names[l] image:nil identifier:nil handler:^(__kindof UIAction *action) { (void)action; dm_pad_layout_set(pick); }];
        a.state = dm_pad_layout() == l ? UIMenuElementStateOn : UIMenuElementStateOff;
        [layouts addObject:a];
    }
    UIMenu *layout = [UIMenu menuWithTitle:@"Controller layout" image:nil identifier:nil options:UIMenuOptionsSingleSelection children:layouts];
    return [UIMenu menuWithTitle:@"" image:nil identifier:nil options:UIMenuOptionsDisplayInline children:@[layout]];
}

void *dm_game_menu(void) {
    UIDeferredMenuElement *deferred = [UIDeferredMenuElement elementWithUncachedProvider:^(void (^completion)(NSArray<UIMenuElement *> *)) { completion(@[game_menu_items()]); }];
    UIMenu *menu = [UIMenu menuWithTitle:@"" children:@[deferred]];
    return (void *)CFBridgingRetain(menu);
}
